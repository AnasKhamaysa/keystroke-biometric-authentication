# Keystroke Biometric Authentication System

A cybersecurity-oriented authentication system that combines **traditional password verification** with **AI-based keystroke biometrics**.

The system analyzes the user's typing rhythm using behavioral features such as **Dwell Time (DT)** and **Flight Time (FT)**, then uses an **Isolation Forest** anomaly detection model to distinguish legitimate users from suspicious login attempts.

> This version represents the project **before Docker containerization**. The frontend and backend are run manually in the local development environment.

---

## Overview

Traditional authentication verifies whether the entered password is correct. This project adds a second security layer by analyzing **how the password is typed**.

The authentication process consists of two stages:

1. **Password Verification** — the entered password is verified securely using `bcrypt`.
2. **Keystroke Biometric Verification** — the user's typing pattern is evaluated using a trained machine learning model.

A login attempt is accepted only after the required authentication checks are successfully completed.

---

## Main Features

- Secure user enrollment
- Collection of **10 typing samples** during enrollment
- Keystroke event capture using JavaScript
- Dwell Time and Flight Time extraction
- Total typing duration calculation
- Password hashing using **bcrypt**
- User and biometric profile storage using **SQLite**
- FastAPI-based backend
- Machine learning anomaly detection using **Isolation Forest**
- Real-time biometric authentication
- Anomaly score extraction
- Authentication audit logging
- Admin dashboard for monitoring login activity
- Input validation and error handling
- XSS-related frontend hardening
- NumPy-based inference optimization
- Manual local frontend and backend execution

---

## System Architecture

```text
User
  |
  v
Frontend (HTML / CSS / JavaScript)
  |
  |-- Capture keydown / keyup events
  |-- Calculate biometric timing features
  |
  v
FastAPI Backend
  |
  |-- Verify password using bcrypt
  |-- Prepare biometric feature vector
  |-- Standardize input data
  |
  v
Isolation Forest Model
  |
  |-- Genuine / Normal Pattern
  |-- Anomalous / Suspicious Pattern
  |
  v
Authentication Decision
  |
  +--> Audit Log --> SQLite Database
```

---

## Keystroke Biometric Features

### Dwell Time (DT)

Dwell Time represents how long a key remains pressed.

```text
DT = KeyUp Time - KeyDown Time
```

### Flight Time (FT)

Flight Time represents the transition time between consecutive keystrokes.

```text
FT = Next KeyDown Time - Current KeyUp Time
```

### Total Duration

The system also calculates the total time required to type the complete password.

These values are combined to create a behavioral biometric profile for the user.

---

## Technology Stack

### Frontend

- HTML
- CSS
- JavaScript
- Fetch API

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

### Database & Security

- SQLite
- bcrypt

### Machine Learning

- Scikit-learn
- Isolation Forest
- StandardScaler
- Pandas
- NumPy
- Joblib

---

## Project Structure

```text
project/
│
├── frontend/
│   ├── index.html
│   ├── admin.html
│   ├── app.js
│   └── style.css
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── biometrics.db
│   └── models/
│       ├── keystroke_model.pkl
│       └── data_scaler.pkl
│
└── ml_model/
    └── model training and preprocessing files
```

---

## Enrollment Workflow

During enrollment:

1. The user chooses a username.
2. The user types the same password **10 times**.
3. JavaScript records `keydown` and `keyup` timestamps.
4. Dwell Time, Flight Time, and total duration are calculated.
5. The biometric samples are organized into a structured JSON payload.
6. The frontend sends the data to the FastAPI `/enroll` endpoint.
7. The backend hashes the password using `bcrypt`.
8. The password hash and biometric profile are stored in SQLite.

The system verifies that the same password is used throughout all enrollment attempts.

---

## Login Workflow

During login:

1. The user enters a username and password.
2. The frontend captures the new typing rhythm.
3. The username, password, and biometric data are sent to the `/login` endpoint.
4. The backend verifies the password using the stored bcrypt hash.
5. If the password is incorrect, authentication is rejected.
6. If the password is correct, the biometric features are prepared for the AI model.
7. The stored scaler standardizes the biometric values.
8. The Isolation Forest model evaluates the typing pattern.
9. The backend returns the authentication result and anomaly score.
10. The attempt is stored in the audit log.

---

## Machine Learning

The project uses the **Isolation Forest** algorithm for anomaly detection.

The model is trained using the legitimate user's enrolled keystroke behavior. It learns the normal typing pattern and identifies significant deviations as possible anomalies.

The trained components are saved using Joblib:

```text
keystroke_model.pkl
data_scaler.pkl
```

This allows the FastAPI backend to load the trained model and perform real-time authentication without retraining during every login request.

---

## API Endpoints

### Enrollment

```http
POST /enroll
```

Registers a new user and stores the user's biometric typing profile.

### Login

```http
POST /login
```

Performs password verification and keystroke biometric authentication.

### Admin Logs

```http
GET /admin/logs
```

Returns authentication audit logs for the administration dashboard.

### Swagger Documentation

After starting the FastAPI backend:

```text
http://127.0.0.1:8000/docs
```

---

## Audit Logging

The system records important information related to authentication attempts, including:

- Timestamp
- Username
- Authentication status
- AI anomaly score

These records can be viewed through the Admin Dashboard.

---

## Admin Dashboard

A standalone administration dashboard was created to display authentication activity.

The dashboard retrieves data from:

```http
GET /admin/logs
```

It allows administrators to monitor:

- Login attempts
- Authentication results
- Suspicious activity
- AI anomaly scores

---

## Security Measures

The project includes several security mechanisms:

- Passwords are stored only as bcrypt hashes.
- Plaintext passwords are not saved in the database.
- Invalid passwords are rejected before AI biometric verification.
- Pasting into biometric password fields is prevented.
- Biometric data is reset between attempts.
- Duplicate usernames are rejected.
- Backend input validation is applied.
- Sensitive browser console output is minimized.
- Safer DOM handling is used in the Admin Dashboard to reduce XSS risks.
- Database connections include improved error handling.
- Missing or invalid AI model data is handled gracefully.

---

## Running the Project Manually

### 1. Start the Backend

Open a terminal and navigate to the backend directory:

```bash
cd backend
```

Install the required Python packages:

```bash
pip install fastapi uvicorn pydantic bcrypt pandas numpy scikit-learn joblib
```

Start the FastAPI server:

```bash
python -m uvicorn main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Swagger API documentation will be available at:

```text
http://127.0.0.1:8000/docs
```

---

### 2. Start the Frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

The frontend can be served using a local development server.

For example, using Python:

```bash
python -m http.server 5500
```

Then open:

```text
http://127.0.0.1:5500
```

---

## Local Development Workflow

Before Docker was introduced, the application required the frontend and backend to be started separately.

```text
Terminal 1:
Frontend Server
    |
    v
http://127.0.0.1:5500

Terminal 2:
FastAPI Backend
    |
    v
http://127.0.0.1:8000
```

Both services must remain active for enrollment, login, AI authentication, and the Admin Dashboard to work correctly.

---

## Project Goal

The main goal of this project is to demonstrate how **behavioral biometrics and machine learning** can strengthen conventional password authentication.

Instead of relying only on something the user knows — the password — the system also evaluates a behavioral characteristic: **the user's typing rhythm**.

---

## Conclusion

This project combines:

- Frontend development
- Backend API development
- Database management
- Cybersecurity
- Behavioral biometrics
- Machine learning
- Real-time anomaly detection
- Security monitoring

The result is a functional **dual-layer authentication system** that combines secure password verification with AI-based keystroke dynamics analysis.

This version represents the application in its **local development stage before Docker containerization and Docker Compose deployment**.
