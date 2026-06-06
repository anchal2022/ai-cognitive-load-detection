# predict_model.py

import os
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error

MODEL_FILE = "cognitive_load_model.joblib"

FEATURE_COLUMNS = [
    "tasks",
    "stress",
    "sleep",
    "deadline",
    "posture",
    "typing_speed",
    "backspace_count",
    "idle_time",
    "mouse_activity",
    "behavioral_load_score",
]


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def calculate_behavioral_load_score(
    typing_speed=0,
    backspace_count=0,
    idle_time=0,
    mouse_activity=0
):
    typing_speed = clamp(float(typing_speed), 0, 100)
    backspace_count = clamp(int(backspace_count), 0, 100)
    idle_time = clamp(int(idle_time), 0, 300)
    mouse_activity = clamp(int(mouse_activity), 0, 500)

    score = 0

    if typing_speed == 0:
        score += 5
    elif typing_speed < 15:
        score += 25
    elif typing_speed < 25:
        score += 15

    if backspace_count >= 30:
        score += 25
    elif backspace_count >= 15:
        score += 15
    elif backspace_count >= 5:
        score += 8

    if idle_time >= 60:
        score += 25
    elif idle_time >= 30:
        score += 15
    elif idle_time >= 15:
        score += 8

    if mouse_activity >= 250:
        score += 15
    elif mouse_activity >= 120:
        score += 8

    return round(clamp(score, 0, 100), 1)


def calculate_cognitive_load_formula(
    tasks,
    stress,
    sleep,
    deadline,
    posture,
    typing_speed=0,
    backspace_count=0,
    idle_time=0,
    mouse_activity=0,
    behavioral_load_score=0
):
    tasks = clamp(int(tasks), 1, 12)
    stress = clamp(float(stress), 1, 10)
    sleep = clamp(float(sleep), 1, 10)
    deadline = clamp(int(deadline), 1, 10)
    posture = clamp(int(posture), 1, 10)

    typing_speed = clamp(float(typing_speed), 0, 100)
    backspace_count = clamp(int(backspace_count), 0, 100)
    idle_time = clamp(int(idle_time), 0, 300)
    mouse_activity = clamp(int(mouse_activity), 0, 500)

    if behavioral_load_score == 0:
        behavioral_load_score = calculate_behavioral_load_score(
            typing_speed=typing_speed,
            backspace_count=backspace_count,
            idle_time=idle_time,
            mouse_activity=mouse_activity
        )

    behavioral_load_score = clamp(float(behavioral_load_score), 0, 100)

    task_risk = tasks / 12
    stress_risk = stress / 10
    deadline_risk = deadline / 10
    sleep_risk = (10 - sleep) / 9
    posture_risk = (10 - posture) / 9
    behavioral_risk = behavioral_load_score / 100

    load = (
        task_risk * 22 +
        stress_risk * 22 +
        sleep_risk * 16 +
        deadline_risk * 18 +
        posture_risk * 10 +
        behavioral_risk * 12
    )

    return round(clamp(load, 0, 100), 1)


def generate_synthetic_data(n=3000):
    rows = []

    for _ in range(n):
        tasks = np.random.randint(1, 13)

        # stress and sleep can be decimal because frontend now converts PSS/PSQI into 1-10 scale
        stress = round(float(np.random.uniform(1, 10)), 1)
        sleep = round(float(np.random.uniform(1, 10)), 1)

        deadline = np.random.randint(1, 11)
        posture = np.random.randint(1, 11)

        typing_speed = np.random.randint(5, 70)
        backspace_count = np.random.randint(0, 40)
        idle_time = np.random.randint(0, 90)
        mouse_activity = np.random.randint(0, 300)

        behavioral_load_score = calculate_behavioral_load_score(
            typing_speed=typing_speed,
            backspace_count=backspace_count,
            idle_time=idle_time,
            mouse_activity=mouse_activity
        )

        cognitive_load = calculate_cognitive_load_formula(
            tasks=tasks,
            stress=stress,
            sleep=sleep,
            deadline=deadline,
            posture=posture,
            typing_speed=typing_speed,
            backspace_count=backspace_count,
            idle_time=idle_time,
            mouse_activity=mouse_activity,
            behavioral_load_score=behavioral_load_score
        )

        rows.append({
            "tasks": tasks,
            "stress": stress,
            "sleep": sleep,
            "deadline": deadline,
            "posture": posture,
            "typing_speed": typing_speed,
            "backspace_count": backspace_count,
            "idle_time": idle_time,
            "mouse_activity": mouse_activity,
            "behavioral_load_score": behavioral_load_score,
            "cognitive_load": cognitive_load
        })

    return pd.DataFrame(rows)


def get_model(force_retrain=False):
    if os.path.exists(MODEL_FILE) and not force_retrain:
        try:
            model = joblib.load(MODEL_FILE)

            if hasattr(model, "n_features_in_") and model.n_features_in_ == len(FEATURE_COLUMNS):
                return model

            print("Old model feature count mismatch. Retraining model...")

        except Exception:
            print("Model loading failed. Retraining model...")

    data = generate_synthetic_data()

    X = data[FEATURE_COLUMNS]
    y = data["cognitive_load"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=180,
        random_state=42,
        max_depth=9
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)

    print("Trained cognitive load model with PSS/PSQI-compatible stress and sleep values")
    print(f"RMSE: {rmse:.2f}")
    print(f"MAE: {mae:.2f}")

    joblib.dump(model, MODEL_FILE)

    return model


def predict_cognitive_load(
    tasks,
    stress,
    sleep,
    deadline,
    posture,
    typing_speed=0,
    backspace_count=0,
    idle_time=0,
    mouse_activity=0,
    behavioral_load_score=0
):
    tasks = clamp(int(tasks), 1, 12)

    # stress comes from PSS converted score
    stress = clamp(float(stress), 1, 10)

    # sleep comes from PSQI converted score
    sleep = clamp(float(sleep), 1, 10)

    deadline = clamp(int(deadline), 1, 10)
    posture = clamp(int(posture), 1, 10)

    typing_speed = clamp(float(typing_speed), 0, 100)
    backspace_count = clamp(int(backspace_count), 0, 100)
    idle_time = clamp(int(idle_time), 0, 300)
    mouse_activity = clamp(int(mouse_activity), 0, 500)

    if behavioral_load_score == 0:
        behavioral_load_score = calculate_behavioral_load_score(
            typing_speed=typing_speed,
            backspace_count=backspace_count,
            idle_time=idle_time,
            mouse_activity=mouse_activity
        )

    behavioral_load_score = clamp(float(behavioral_load_score), 0, 100)

    model = get_model()

    X_new = pd.DataFrame([{
        "tasks": tasks,
        "stress": stress,
        "sleep": sleep,
        "deadline": deadline,
        "posture": posture,
        "typing_speed": typing_speed,
        "backspace_count": backspace_count,
        "idle_time": idle_time,
        "mouse_activity": mouse_activity,
        "behavioral_load_score": behavioral_load_score
    }])

    ml_prediction = float(model.predict(X_new)[0])

    formula_prediction = calculate_cognitive_load_formula(
        tasks=tasks,
        stress=stress,
        sleep=sleep,
        deadline=deadline,
        posture=posture,
        typing_speed=typing_speed,
        backspace_count=backspace_count,
        idle_time=idle_time,
        mouse_activity=mouse_activity,
        behavioral_load_score=behavioral_load_score
    )

    final_load = (0.6 * ml_prediction) + (0.4 * formula_prediction)
    final_load = round(clamp(final_load, 0, 100), 1)

    if final_load >= 75:
        risk = "High Overload"
    elif final_load >= 45:
        risk = "Moderate Load"
    else:
        risk = "Low Load"

    return final_load, risk


if __name__ == "__main__":
    get_model(force_retrain=True)

    print("Low load test:", predict_cognitive_load(2, 2.5, 9.2, 2, 9, 45, 1, 2, 20, 5))
    print("Medium load test:", predict_cognitive_load(6, 5.8, 6.1, 5, 6, 25, 8, 20, 100, 30))
    print("High load test:", predict_cognitive_load(12, 9.5, 2.8, 10, 3, 8, 30, 70, 250, 80))