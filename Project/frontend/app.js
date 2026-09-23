// ============================================================
// Keystroke Biometric Authentication Frontend
// ============================================================


// ============================================================
// Global State
// ============================================================

// Stores raw keyboard events for the active typing attempt
let rawKeystrokes = [];


// Enrollment state
let enrollmentAttempts = [];

let currentAttemptCount = 0;

const MAX_ATTEMPTS = 10;

let referencePassword = "";

let enrollmentUsername = "";


// Backend API address
const API_BASE_URL =
    "http://127.0.0.1:8000";


// Keys that should not become biometric typing features
const IGNORED_KEYS = new Set([
    "Shift",
    "Control",
    "Alt",
    "Meta",
    "CapsLock",
    "Tab",
    "Escape",
    "Enter",
    "ArrowLeft",
    "ArrowRight",
    "ArrowUp",
    "ArrowDown",
    "Home",
    "End",
    "PageUp",
    "PageDown"
]);


// ============================================================
// Raw Keystroke Capture
// ============================================================

function captureKeystroke(event) {

    // Ignore automatically repeated keydown events
    if (
        event.type === "keydown" &&
        event.repeat
    ) {
        return;
    }


    // Ignore modifier/navigation keys
    if (
        IGNORED_KEYS.has(
            event.key
        )
    ) {
        return;
    }


    // Backspace and Delete require the typing attempt
    // to be restarted to preserve biometric consistency.
    if (
        event.key === "Backspace" ||
        event.key === "Delete"
    ) {
        return;
    }


    const timestamp =
        performance.now();


    rawKeystrokes.push({

        key:
            event.key,

        action:
            event.type,

        time:
            timestamp
    });
}


// ============================================================
// Input Handling
// ============================================================

function handleInputChanges(event) {

    const inputType =
        event.inputType || "";


    // If the user deletes characters, restart the entire
    // biometric attempt to prevent stale timings.
    if (
        inputType.startsWith(
            "delete"
        )
    ) {

        rawKeystrokes = [];

        event.target.value = "";

        console.log(
            "Typing attempt reset after deletion."
        );

        return;
    }


    // Reset capture if the field becomes empty
    if (
        event.target.value === ""
    ) {

        rawKeystrokes = [];
    }
}


// ============================================================
// Paste Prevention
// ============================================================

function preventPaste(event) {

    event.preventDefault();

    alert(
        "Pasting is disabled because the system must measure your natural typing rhythm."
    );
}


// ============================================================
// Session Reset
// ============================================================

function resetKeystrokeSession() {

    rawKeystrokes = [];
}


// ============================================================
// Keyboard Initialization
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const loginPassword =
            document.getElementById(
                "login-password"
            );


        const enrollPassword =
            document.getElementById(
                "enroll-password"
            );


        if (loginPassword) {

            loginPassword.addEventListener(
                "focus",
                resetKeystrokeSession
            );

            loginPassword.addEventListener(
                "keydown",
                captureKeystroke
            );

            loginPassword.addEventListener(
                "keyup",
                captureKeystroke
            );

            loginPassword.addEventListener(
                "input",
                handleInputChanges
            );

            loginPassword.addEventListener(
                "paste",
                preventPaste
            );
        }


        if (enrollPassword) {

            enrollPassword.addEventListener(
                "focus",
                resetKeystrokeSession
            );

            enrollPassword.addEventListener(
                "keydown",
                captureKeystroke
            );

            enrollPassword.addEventListener(
                "keyup",
                captureKeystroke
            );

            enrollPassword.addEventListener(
                "input",
                handleInputChanges
            );

            enrollPassword.addEventListener(
                "paste",
                preventPaste
            );
        }
    }
);


// ============================================================
// Feature Extraction
// ============================================================

function processKeystrokes() {

    const processedData = {

        dwellTimes: [],

        flightTimes: [],

        totalDuration: 0
    };


    if (
        rawKeystrokes.length === 0
    ) {

        return processedData;
    }


    const keydowns =
        rawKeystrokes.filter(
            event =>
                event.action ===
                "keydown"
        );


    const keyups =
        rawKeystrokes.filter(
            event =>
                event.action ===
                "keyup"
        );


    const matchedPairs = [];

    const usedKeyupIndexes =
        new Set();


    // ========================================================
    // Match Keydown and Keyup Events
    // ========================================================

    for (
        let i = 0;
        i < keydowns.length;
        i++
    ) {

        const keydown =
            keydowns[i];


        let matchingKeyup =
            null;

        let matchingIndex =
            -1;


        for (
            let j = 0;
            j < keyups.length;
            j++
        ) {

            if (
                usedKeyupIndexes.has(j)
            ) {
                continue;
            }


            const keyup =
                keyups[j];


            if (
                keyup.key ===
                    keydown.key &&
                keyup.time >=
                    keydown.time
            ) {

                matchingKeyup =
                    keyup;

                matchingIndex =
                    j;

                break;
            }
        }


        if (matchingKeyup) {

            usedKeyupIndexes.add(
                matchingIndex
            );


            matchedPairs.push({

                keydown:
                    keydown,

                keyup:
                    matchingKeyup
            });
        }
    }


    // ========================================================
    // Dwell Time
    // ========================================================

    for (
        let i = 0;
        i < matchedPairs.length;
        i++
    ) {

        const pair =
            matchedPairs[i];


        const dwellTime =
            pair.keyup.time -
            pair.keydown.time;


        processedData
            .dwellTimes
            .push({

                key:
                    pair.keydown.key,

                dt:
                    parseFloat(
                        dwellTime.toFixed(2)
                    )
            });
    }


    // ========================================================
    // Flight Time
    // ========================================================

    for (
        let i = 0;
        i < matchedPairs.length - 1;
        i++
    ) {

        const currentPair =
            matchedPairs[i];


        const nextPair =
            matchedPairs[
                i + 1
            ];


        const flightTime =
            nextPair.keydown.time -
            currentPair.keyup.time;


        processedData
            .flightTimes
            .push({

                transition:
                    `${currentPair.keydown.key} -> ${nextPair.keydown.key}`,

                ft:
                    parseFloat(
                        flightTime.toFixed(2)
                    )
            });
    }


    // ========================================================
    // Total Duration
    // ========================================================

    if (
        matchedPairs.length > 0
    ) {

        const firstKeydown =
            matchedPairs[0]
                .keydown
                .time;


        const lastKeyup =
            matchedPairs[
                matchedPairs.length - 1
            ]
                .keyup
                .time;


        processedData.totalDuration =
            parseFloat(
                (
                    lastKeyup -
                    firstKeydown
                ).toFixed(2)
            );
    }


    return processedData;
}


// ============================================================
// Login
// ============================================================

document
    .getElementById(
        "login-form"
    )
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const usernameField =
                document.getElementById(
                    "login-username"
                );


            const passwordField =
                document.getElementById(
                    "login-password"
                );


            const username =
                usernameField.value.trim();


            const password =
                passwordField.value;


            const biometricProfile =
                processKeystrokes();


            if (
                biometricProfile
                    .dwellTimes
                    .length === 0
            ) {

                alert(
                    "Please type your password manually."
                );

                return;
            }


            const loginPayload = {

                username:
                    username,

                password:
                    password,

                biometric_data:
                    biometricProfile
            };


            try {

                const response =
                    await fetch(
                        `${API_BASE_URL}/login`,
                        {

                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(
                                    loginPayload
                                )
                        }
                    );


                const result =
                    await response.json();


                if (response.ok) {

                    alert(
                        result.message
                    );

                } else {

                    alert(
                        "Error: " +
                        (
                            result.detail ||
                            "Authentication failed."
                        )
                    );
                }

            } catch (error) {

                console.error(
                    "Network Error:",
                    error
                );


                alert(
                    "Unable to connect to the authentication server."
                );

            } finally {

                rawKeystrokes = [];

                passwordField.value = "";

                passwordField.focus();
            }
        }
    );


// ============================================================
// Enrollment Helper
// ============================================================

function resetEnrollmentState() {

    enrollmentAttempts = [];

    currentAttemptCount = 0;

    referencePassword = "";

    enrollmentUsername = "";

    rawKeystrokes = [];


    const usernameField =
        document.getElementById(
            "enroll-username"
        );


    const passwordField =
        document.getElementById(
            "enroll-password"
        );


    const attemptCounter =
        document.getElementById(
            "attempt-count"
        );


    usernameField.value = "";

    usernameField.disabled = false;

    passwordField.value = "";

    attemptCounter.innerText = "0";
}


// ============================================================
// Send Enrollment Profile
// ============================================================

async function sendEnrollmentProfile() {

    const passwordField =
        document.getElementById(
            "enroll-password"
        );


    const finalEnrollmentProfile = {

        username:
            enrollmentUsername,

        password:
            referencePassword,

        attempts:
            enrollmentAttempts
    };


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/enroll`,
                {

                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            finalEnrollmentProfile
                        )
                }
            );


        const result =
            await response.json();


        if (response.ok) {

            alert(
                "Success: " +
                result.message
            );


            resetEnrollmentState();


            // Return to login page
            toggleView();


        } else {

            alert(
                "Error: " +
                (
                    result.detail ||
                    "Enrollment failed."
                )
            );


            resetEnrollmentState();

            passwordField.focus();
        }


    } catch (error) {

        console.error(
            "Network Error:",
            error
        );


        alert(
            "Failed to connect to the server. Your collected attempts are still available. Press Submit Attempt again to retry."
        );


        passwordField.value = "";
    }
}


// ============================================================
// Enrollment
// ============================================================

document
    .getElementById(
        "enroll-form"
    )
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const usernameField =
                document.getElementById(
                    "enroll-username"
                );


            const passwordField =
                document.getElementById(
                    "enroll-password"
                );


            // If 10 attempts already exist, this is a retry
            // after a temporary network failure.
            if (
                currentAttemptCount >=
                MAX_ATTEMPTS
            ) {

                await sendEnrollmentProfile();

                return;
            }


            const username =
                usernameField.value.trim();


            const currentPassword =
                passwordField.value;


            // ====================================================
            // Basic Validation
            // ====================================================

            if (
                username.length < 3
            ) {

                alert(
                    "Username must contain at least 3 characters."
                );

                return;
            }


            if (
                currentPassword.length < 4
            ) {

                alert(
                    "Password must contain at least 4 characters."
                );

                return;
            }


            // ====================================================
            // First Attempt
            // ====================================================

            if (
                currentAttemptCount === 0
            ) {

                referencePassword =
                    currentPassword;


                enrollmentUsername =
                    username;


                // Prevent changing username halfway
                // through enrollment.
                usernameField.disabled =
                    true;

            } else {

                if (
                    currentPassword !==
                    referencePassword
                ) {

                    alert(
                        "Password does not match the first attempt. Please type exactly the same password."
                    );


                    rawKeystrokes = [];

                    passwordField.value = "";

                    passwordField.focus();

                    return;
                }
            }


            // ====================================================
            // Process Biometric Sample
            // ====================================================

            const biometricAttempt =
                processKeystrokes();


            if (
                biometricAttempt
                    .dwellTimes
                    .length === 0
            ) {

                alert(
                    "Please type the password manually."
                );


                rawKeystrokes = [];

                passwordField.value = "";

                passwordField.focus();

                return;
            }


            // ====================================================
            // Structural Consistency Check
            // ====================================================

            if (
                enrollmentAttempts.length > 0
            ) {

                const referenceDwellCount =
                    enrollmentAttempts[0]
                        .dwellTimes
                        .length;


                const referenceFlightCount =
                    enrollmentAttempts[0]
                        .flightTimes
                        .length;


                if (
                    biometricAttempt
                        .dwellTimes
                        .length !==
                        referenceDwellCount ||

                    biometricAttempt
                        .flightTimes
                        .length !==
                        referenceFlightCount
                ) {

                    alert(
                        "This typing attempt has a different keystroke structure. Please type the password again normally."
                    );


                    rawKeystrokes = [];

                    passwordField.value = "";

                    passwordField.focus();

                    return;
                }
            }


            // ====================================================
            // Save Attempt
            // ====================================================

            enrollmentAttempts.push(
                biometricAttempt
            );


            currentAttemptCount++;


            document
                .getElementById(
                    "attempt-count"
                )
                .innerText =
                    currentAttemptCount;


            rawKeystrokes = [];

            passwordField.value = "";


            // ====================================================
            // Continue Collecting
            // ====================================================

            if (
                currentAttemptCount <
                MAX_ATTEMPTS
            ) {

                passwordField.focus();

                return;
            }


            // ====================================================
            // Complete Enrollment
            // ====================================================

            await sendEnrollmentProfile();
        }
    );