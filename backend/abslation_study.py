# ablation_study.py

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from predict_model import generate_synthetic_data


OUTPUT_DIR = "../research/research_outputs"


# ------------------------------
# Safe directory creation
# ------------------------------
def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------
# Model Evaluation Helper
# ------------------------------
def evaluate_model(data, feature_columns, model_name):
    """
    Trains and evaluates a Random Forest model using selected features.
    This helps compare how each feature group improves prediction.
    """

    X = data[feature_columns]
    y = data["cognitive_load"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=150,
        random_state=42,
        max_depth=8
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    return {
        "Model": model_name,
        "Features Used": ", ".join(feature_columns),
        "RMSE": round(rmse, 2),
        "MAE": round(mae, 2),
        "R2 Score": round(r2, 2)
    }


# ------------------------------
# Ablation Study
# ------------------------------
def run_ablation_study(n_samples=3000):
    """
    Ablation study checks how each module contributes to prediction.

    Model 1: Task factors only
    Model 2: Task + posture
    Model 3: Task + posture + behavioral features
    Model 4: Full FlowMind multimodal model
    """

    ensure_output_dir()

    data = generate_synthetic_data(n_samples)

    experiments = [
        {
            "name": "Task Factors Only",
            "features": ["tasks", "stress", "sleep", "deadline"]
        },
        {
            "name": "Task + Posture",
            "features": ["tasks", "stress", "sleep", "deadline", "posture"]
        },
        {
            "name": "Task + Posture + Behavior",
            "features": [
                "tasks",
                "stress",
                "sleep",
                "deadline",
                "posture",
                "typing_speed",
                "backspace_count",
                "idle_time",
                "mouse_activity"
            ]
        },
        {
            "name": "Full FlowMind Model",
            "features": [
                "tasks",
                "stress",
                "sleep",
                "deadline",
                "posture",
                "typing_speed",
                "backspace_count",
                "idle_time",
                "mouse_activity",
                "behavioral_load_score"
            ]
        }
    ]

    results = []

    for experiment in experiments:
        result = evaluate_model(
            data=data,
            feature_columns=experiment["features"],
            model_name=experiment["name"]
        )
        results.append(result)

    results_df = pd.DataFrame(results)

    output_csv = os.path.join(OUTPUT_DIR, "ablation_results.csv")
    results_df.to_csv(output_csv, index=False)

    generate_ablation_graph(results_df)

    return results_df


# ------------------------------
# Ablation Graph
# ------------------------------
def generate_ablation_graph(results_df):
    """
    Creates a graph comparing R2 score of different model versions.
    Higher R2 means better prediction.
    """

    plt.figure(figsize=(9, 5))
    plt.bar(results_df["Model"], results_df["R2 Score"])
    plt.xlabel("Model Version")
    plt.ylabel("R2 Score")
    plt.title("Ablation Study: Contribution of Feature Groups")
    plt.ylim(0, 1)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, "figure_ablation_study.png")
    plt.savefig(output_path, dpi=300)
    plt.close()


# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    results = run_ablation_study()

    print("Ablation study completed successfully.")
    print(results)
    print(f"Results saved in: {OUTPUT_DIR}")