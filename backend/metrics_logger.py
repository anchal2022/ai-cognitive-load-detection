# metrics_logger.py

import os
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score

AUTO_LOG_FILE = "user_metrics.csv"
EXPERIMENT_LOG_FILE = "experiment_sessions.csv"


def safe_read_csv(file_path):
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path)
    except Exception:
        return pd.DataFrame()


def compute_auto_log_metrics():
    """
    Computes metrics from automatic logs.
    These logs are generated every few seconds, so they are not treated as final research sessions.
    """

    df = safe_read_csv(AUTO_LOG_FILE)

    if df.empty:
        return {
            "totalAutoLogs": 0,
            "message": "No auto logs found."
        }

    if "cognitiveLoad" not in df.columns or "improvedLoad" not in df.columns:
        return {
            "totalAutoLogs": len(df),
            "message": "Auto log file exists but required columns are missing."
        }

    df["cognitiveLoad"] = pd.to_numeric(df["cognitiveLoad"], errors="coerce")
    df["improvedLoad"] = pd.to_numeric(df["improvedLoad"], errors="coerce")
    df = df.dropna(subset=["cognitiveLoad", "improvedLoad"])

    if df.empty:
        return {
            "totalAutoLogs": 0,
            "message": "No valid numeric auto logs found."
        }

    reduction = df["cognitiveLoad"] - df["improvedLoad"]

    return {
        "totalAutoLogs": int(len(df)),
        "averageAutoLoad": round(df["cognitiveLoad"].mean(), 1),
        "averageAutoImprovedLoad": round(df["improvedLoad"].mean(), 1),
        "averageAutoReduction": round(reduction.mean(), 1),
        "averageAutoReductionPercent": round((reduction.mean() / df["cognitiveLoad"].mean()) * 100, 1),
        "message": "Auto log metrics computed successfully."
    }


def compute_experiment_metrics():
    """
    Computes research-grade metrics from manually saved experiment sessions.
    These are the valid sessions for report/paper validation.
    """

    df = safe_read_csv(EXPERIMENT_LOG_FILE)

    if df.empty:
        return {
            "validExperimentSessions": 0,
            "message": "No experiment sessions saved yet."
        }

    required_cols = ["baselineLoad", "flowmindLoad", "improvement", "improvementPercent"]

    for col in required_cols:
        if col not in df.columns:
            return {
                "validExperimentSessions": 0,
                "message": f"Experiment log exists but missing column: {col}"
            }

    df["baselineLoad"] = pd.to_numeric(df["baselineLoad"], errors="coerce")
    df["flowmindLoad"] = pd.to_numeric(df["flowmindLoad"], errors="coerce")
    df["improvement"] = pd.to_numeric(df["improvement"], errors="coerce")
    df["improvementPercent"] = pd.to_numeric(df["improvementPercent"], errors="coerce")

    df = df.dropna(subset=["baselineLoad", "flowmindLoad", "improvement", "improvementPercent"])

    if df.empty:
        return {
            "validExperimentSessions": 0,
            "message": "No valid numeric experiment sessions found."
        }

    rmse = np.sqrt(mean_squared_error(df["baselineLoad"], df["flowmindLoad"]))

    try:
        r2 = r2_score(df["baselineLoad"], df["flowmindLoad"])
    except Exception:
        r2 = 0

    return {
        "validExperimentSessions": int(len(df)),
        "baselineAverageLoad": round(df["baselineLoad"].mean(), 1),
        "flowmindAverageLoad": round(df["flowmindLoad"].mean(), 1),
        "averageReduction": round(df["improvement"].mean(), 1),
        "averageReductionPercent": round(df["improvementPercent"].mean(), 1),
        "rmseBaselineVsFlowMind": round(rmse, 2),
        "r2BaselineVsFlowMind": round(r2, 2),
        "message": "Experiment metrics computed successfully."
    }


def compute_metrics():
    auto_metrics = compute_auto_log_metrics()
    experiment_metrics = compute_experiment_metrics()

    print("Auto Log Metrics:")
    print(auto_metrics)

    print("\nExperiment Session Metrics:")
    print(experiment_metrics)


if __name__ == "__main__":
    compute_metrics()