# ============================================================
# Keystroke Biometric Authentication Backend
# ============================================================

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import pandas as pd
import bcrypt
import joblib
import hashlib

from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

from database import (
    init_db,
    add_user,
    delete_user,
    username_exists,
    get_user_password_hash,
    add_audit_log,
    get_all_audit_logs
)


# ============================================================
# Application Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODELS_DIR = BASE_DIR / "models"

MODELS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# Application Initialization
# ============================================================

app = FastAPI(
    title="Keystroke Biometric Authentication API",
    version="2.0"
)


# ============================================================
# CORS Configuration
# ============================================================

# Local-development frontend origins.
#
# The frontend should preferably be started using:
#
# python -m http.server 5500
#
# inside the frontend folder.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Database Initialization
# ============================================================

init_db()


# ============================================================
# Utility Functions
# ============================================================

def get_model_path(username):
    """
    Create a safe model filename for a user.

    A SHA-256 hash is used instead of placing the username
    directly inside the filesystem path.
    """

    username_hash = hashlib.sha256(
        username.encode("utf-8")
    ).hexdigest()

    return (
        MODELS_DIR /
        f"{username_hash}_biometric_model.pkl"
    )


def validate_username(username):
    """
    Perform basic username validation.
    """

    if not isinstance(username, str):
        return False

    username = username.strip()

    if len(username) < 3:
        return False

    if len(username) > 50:
        return False

    return True


# ============================================================
# Biometric Feature Extraction
# ============================================================

def extract_features(biometric_data):
    """
    Convert one keystroke attempt into machine-learning features.

    IMPORTANT:

    Features use positional indexes instead of key names.

    Example:

        DT_0
        DT_1
        DT_2

        FT_0
        FT_1

    This fixes the old problem where repeated characters such as
    the two 'l' characters in "hello" overwrote each other.
    """

    if not isinstance(
        biometric_data,
        dict
    ):
        raise ValueError(
            "Biometric attempt must be an object."
        )


    dwell_times = biometric_data.get(
        "dwellTimes"
    )

    flight_times = biometric_data.get(
        "flightTimes"
    )


    if not isinstance(
        dwell_times,
        list
    ):
        raise ValueError(
            "Invalid dwell-time data."
        )


    if not isinstance(
        flight_times,
        list
    ):
        raise ValueError(
            "Invalid flight-time data."
        )


    if len(dwell_times) == 0:
        raise ValueError(
            "No dwell-time features were provided."
        )


    row = {}


    # ========================================================
    # Dwell Times
    # ========================================================

    for index, dt_object in enumerate(
        dwell_times
    ):

        if not isinstance(
            dt_object,
            dict
        ):
            raise ValueError(
                "Invalid dwell-time entry."
            )

        dt_value = dt_object.get("dt")

        if dt_value is None:
            raise ValueError(
                "Missing dwell-time value."
            )

        dt_value = float(dt_value)

        if not np.isfinite(dt_value):
            raise ValueError(
                "Invalid dwell-time value."
            )

        if dt_value < 0:
            raise ValueError(
                "Negative dwell-time detected."
            )

        row[
            f"DT_{index}"
        ] = dt_value


    # ========================================================
    # Flight Times
    # ========================================================

    for index, ft_object in enumerate(
        flight_times
    ):

        if not isinstance(
            ft_object,
            dict
        ):
            raise ValueError(
                "Invalid flight-time entry."
            )

        ft_value = ft_object.get("ft")

        if ft_value is None:
            raise ValueError(
                "Missing flight-time value."
            )

        ft_value = float(ft_value)

        if not np.isfinite(ft_value):
            raise ValueError(
                "Invalid flight-time value."
            )

        # Negative flight time is valid because adjacent key
        # presses can overlap naturally.

        row[
            f"FT_{index}"
        ] = ft_value


    # ========================================================
    # Total Duration
    # ========================================================

    try:

        total_duration = float(
            biometric_data.get(
                "totalDuration",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        raise ValueError(
            "Invalid total typing duration."
        )


    if not np.isfinite(
        total_duration
    ):
        raise ValueError(
            "Invalid total typing duration."
        )


    row[
        "Total_Duration"
    ] = total_duration


    return row


# ============================================================
# Enrollment Model Training
# ============================================================

def train_user_model(
    username,
    biometric_attempts
):
    """
    Train a separate anomaly-detection model for one user.

    Each user receives:

    - StandardScaler
    - IsolationForest
    - Expected feature names
    - User-specific decision threshold
    """

    if not isinstance(
        biometric_attempts,
        list
    ):

        raise ValueError(
            "Enrollment attempts must be a list."
        )


    if len(
        biometric_attempts
    ) < 5:

        raise ValueError(
            "At least 5 biometric attempts are required."
        )


    feature_rows = []


    # ========================================================
    # Extract Enrollment Features
    # ========================================================

    for attempt in biometric_attempts:

        row = extract_features(
            attempt
        )

        feature_rows.append(
            row
        )


    # ========================================================
    # Verify Structural Consistency
    # ========================================================

    expected_feature_names = list(
        feature_rows[0].keys()
    )

    expected_feature_set = set(
        expected_feature_names
    )


    for row in feature_rows:

        if set(row.keys()) != expected_feature_set:

            raise ValueError(
                "Enrollment attempts contain inconsistent "
                "keystroke structures. Please type the password "
                "normally and consistently."
            )


    # ========================================================
    # Build Training DataFrame
    # ========================================================

    training_df = pd.DataFrame(
        feature_rows,
        columns=expected_feature_names
    )


    if training_df.isnull().any().any():

        raise ValueError(
            "Enrollment data contains missing values."
        )


    # ========================================================
    # Feature Scaling
    # ========================================================

    scaler = StandardScaler()

    scaled_training_data = (
        scaler.fit_transform(
            training_df
        )
    )


    # ========================================================
    # Isolation Forest Training
    # ========================================================

    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42
    )


    model.fit(
        scaled_training_data
    )


    # ========================================================
    # User-Specific Threshold
    # ========================================================

    training_scores = (
        model.decision_function(
            scaled_training_data
        )
    )


    # The lower percentile represents the weaker genuine
    # enrollment samples.
    #
    # A small margin helps prevent unnecessary rejection
    # of the legitimate user.

    threshold = float(
        np.percentile(
            training_scores,
            5
        ) - 0.01
    )


    # ========================================================
    # Save User Model Bundle
    # ========================================================

    model_bundle = {

        "username":
            username,

        "model":
            model,

        "scaler":
            scaler,

        "feature_columns":
            expected_feature_names,

        "threshold":
            threshold,

        "training_sample_count":
            len(feature_rows)
    }


    model_path = get_model_path(
        username
    )


    joblib.dump(
        model_bundle,
        model_path
    )


    return model_path


# ============================================================
# Enrollment Endpoint
# ============================================================

@app.post("/enroll")
async def enroll(
    request: Request
):

    """
    Register a user and automatically train a unique
    keystroke biometric model for that user.
    """

    try:

        data = await request.json()

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid JSON request."
        )


    username = data.get(
        "username"
    )

    password = data.get(
        "password"
    )

    biometric_data = (
        data.get("attempts")
        or
        data.get("biometric_data")
    )


    # ========================================================
    # Input Validation
    # ========================================================

    if not validate_username(
        username
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Username must contain between "
                "3 and 50 characters."
            )
        )


    username = username.strip()


    if not isinstance(
        password,
        str
    ) or len(password) < 4:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain at least "
                "4 characters."
            )
        )


    if not isinstance(
        biometric_data,
        list
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid biometric enrollment data."
            )
        )


    if len(
        biometric_data
    ) < 5:

        raise HTTPException(
            status_code=400,
            detail=(
                "Insufficient biometric enrollment samples."
            )
        )


    # ========================================================
    # Duplicate User Check
    # ========================================================

    if username_exists(
        username
    ):

        raise HTTPException(
            status_code=400,
            detail="Username already exists."
        )


    # ========================================================
    # Train Biometric Model
    # ========================================================

    try:

        train_user_model(
            username,
            biometric_data
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        print(
            f"Model training error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to train biometric profile."
            )
        )


    # ========================================================
    # Password Hashing
    # ========================================================

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


    # ========================================================
    # Save User
    # ========================================================

    try:

        success = add_user(
            username,
            hashed_password,
            biometric_data
        )

    except Exception as error:

        print(
            f"Database enrollment error: {error}"
        )

        # Remove model if database creation failed
        model_path = get_model_path(
            username
        )

        if model_path.exists():
            model_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Unable to complete enrollment."
        )


    if not success:

        model_path = get_model_path(
            username
        )

        if model_path.exists():
            model_path.unlink()

        raise HTTPException(
            status_code=400,
            detail="Username already exists."
        )


    try:

        add_audit_log(
            username,
            "USER_ENROLLED",
            None
        )

    except Exception as error:

        print(
            f"Enrollment audit log error: {error}"
        )


    return {
        "message":
            (
                "User enrolled successfully. "
                "A personal biometric model was created."
            )
    }


# ============================================================
# Login Endpoint
# ============================================================

@app.post("/login")
async def login(
    request: Request
):

    """
    Authenticate using:

    1. Password verification.
    2. User-specific keystroke biometric model.
    """

    try:

        data = await request.json()

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid JSON request."
        )


    username = data.get(
        "username"
    )

    password = data.get(
        "password"
    )

    biometric_data = data.get(
        "biometric_data"
    )


    # ========================================================
    # Basic Validation
    # ========================================================

    if (
        not isinstance(username, str)
        or
        not isinstance(password, str)
    ):

        raise HTTPException(
            status_code=400,
            detail="Missing username or password."
        )


    username = username.strip()


    # ========================================================
    # Password Authentication
    # ========================================================

    try:

        stored_password_hash = (
            get_user_password_hash(
                username
            )
        )

    except Exception as error:

        print(
            f"Database login error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Database error during authentication."
            )
        )


    # Use the same response for unknown username and
    # incorrect password to reduce username enumeration.

    if stored_password_hash is None:

        try:
            add_audit_log(
                username,
                "INVALID_CREDENTIALS",
                None
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=401,
            detail=(
                "Access Denied! Invalid username or password."
            )
        )


    try:

        password_matches = bcrypt.checkpw(
            password.encode("utf-8"),
            stored_password_hash.encode(
                "utf-8"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        raise HTTPException(
            status_code=500,
            detail="Stored password data is invalid."
        )


    if not password_matches:

        try:
            add_audit_log(
                username,
                "INVALID_CREDENTIALS",
                None
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=401,
            detail=(
                "Access Denied! Invalid username or password."
            )
        )


    # ========================================================
    # Biometric Validation
    # ========================================================

    if not isinstance(
        biometric_data,
        dict
    ):

        raise HTTPException(
            status_code=400,
            detail="Missing biometric data."
        )


    try:

        total_duration = float(
            biometric_data.get(
                "totalDuration",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid typing duration."
        )


    # ========================================================
    # Basic Behavioral Security Rules
    # ========================================================

    if total_duration < 150:

        try:
            add_audit_log(
                username,
                "BOT_SUSPECTED",
                None
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=401,
            detail=(
                "Access Denied! Suspiciously fast "
                "typing was detected."
            )
        )


    if total_duration > 15000:

        try:
            add_audit_log(
                username,
                "TYPING_TOO_SLOW",
                None
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=400,
            detail=(
                "Typing was too slow or interrupted. "
                "Please try again normally."
            )
        )


    # ========================================================
    # Load User-Specific Model
    # ========================================================

    model_path = get_model_path(
        username
    )


    if not model_path.exists():

        raise HTTPException(
            status_code=503,
            detail=(
                "Biometric model for this user "
                "is currently unavailable."
            )
        )


    try:

        model_bundle = joblib.load(
            model_path
        )

        model = model_bundle[
            "model"
        ]

        scaler = model_bundle[
            "scaler"
        ]

        expected_columns = model_bundle[
            "feature_columns"
        ]

        threshold = float(
            model_bundle[
                "threshold"
            ]
        )

    except Exception as error:

        print(
            f"Model loading error: {error}"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to load biometric model."
            )
        )


    # ========================================================
    # Feature Extraction
    # ========================================================

    try:

        row = extract_features(
            biometric_data
        )

    except ValueError as error:

        try:
            add_audit_log(
                username,
                "INVALID_BIOMETRIC_DATA",
                None
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    # ========================================================
    # Structural Validation
    # ========================================================

    if set(row.keys()) != set(
        expected_columns
    ):

        try:
            add_audit_log(
                username,
                "BIOMETRIC_STRUCTURE_MISMATCH",
                None
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=401,
            detail=(
                "Access Denied! The typing pattern "
                "structure does not match enrollment."
            )
        )


    # ========================================================
    # Prepare Model Input
    # ========================================================

    try:

        attempt_df = pd.DataFrame(
            [row],
            columns=expected_columns
        )


        scaled_attempt = (
            scaler.transform(
                attempt_df
            )
        )


        anomaly_score = float(
            model.decision_function(
                scaled_attempt
            )[0]
        )


    except Exception as error:

        print(
            f"Biometric model processing error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Error processing biometric data."
            )
        )


    # ========================================================
    # Final Authentication Decision
    # ========================================================

    accepted = (
        anomaly_score >= threshold
    )


    if accepted:

        try:

            add_audit_log(
                username,
                "Accepted",
                anomaly_score
            )

        except Exception as error:

            print(
                f"Audit logging error: {error}"
            )


        return {
            "message":
                (
                    "Access Granted! 🟢 "
                    f"Score: {anomaly_score:.4f}"
                ),

            "anomaly_score":
                anomaly_score,

            "threshold":
                threshold
        }


    try:

        add_audit_log(
            username,
            "Rejected",
            anomaly_score
        )

    except Exception as error:

        print(
            f"Audit logging error: {error}"
        )


    raise HTTPException(
        status_code=401,
        detail=(
            "Access Denied! 🔴 "
            "The typing pattern does not match "
            "the enrolled user. "
            f"Score: {anomaly_score:.4f}"
        )
    )


# ============================================================
# Admin Dashboard
# ============================================================

@app.get("/admin/logs")
async def view_audit_logs():
    """
    Retrieve authentication audit logs.
    """

    try:

        logs = get_all_audit_logs()

    except Exception as error:

        print(
            f"Audit log retrieval error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve audit logs."
            )
        )


    return {

        "message":
            (
                "Audit logs retrieved successfully."
                if logs
                else
                "No logs found yet."
            ),

        "total_records":
            len(logs),

        "data":
            logs
    }


# ============================================================
# Health Check
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "online",
        "system":
            "Keystroke Biometric Authentication API"
    }