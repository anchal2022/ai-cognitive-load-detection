# validation.py

import os
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from predict_model import get_model, generate_synthetic_data, FEATURE_COLUMNS


AUTO_LOG_FILE = "user_metrics.csv"
EXPERIMENT_LOG_FILE = "experiment_sessions.csv"


def safe_read_csv(file_path):
    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        return pd.read_csv(file_path)
    except Exception:
        return pd.DataFrame()


def safe_correlation(series_1, series_2):
    if len(series_1) < 2 or len(series_2) < 2:
        return 0

    if series_1.nunique() <= 1 or series_2.nunique() <= 1:
        return 0

    corr = series_1.corr(series_2)

    if pd.isna(corr):
        return 0

    return round(float(corr), 2)


def validate_model(n_samples=1000):
    data = generate_synthetic_data(n_samples)

    X = data[FEATURE_COLUMNS]
    y_true = data["cognitive_load"]

    model = get_model()
    y_pred = model.predict(X)

    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    return {
        "samples": n_samples,
        "rmse": round(rmse, 2),
        "mae": round(mae, 2),
        "r2Score": round(r2, 2),
    }


def analyze_auto_logs():
    df = safe_read_csv(AUTO_LOG_FILE)

    if df.empty:
        return {
            "totalAutoLogs": 0,
            "averageAutoLoad": 0,
            "averageAutoImprovedLoad": 0,
            "averageAutoImprovement": 0,
            "averageAutoImprovementPercent": 0,
            "averageBehavioralLoad": 0,
            "averageNasaTlxScore": 0,
            "averagePssScore": 0,
            "averagePsqiScore": 0,
            "message": "No auto logs found yet.",
        }

    if "cognitiveLoad" not in df.columns or "improvedLoad" not in df.columns:
        return {
            "totalAutoLogs": int(len(df)),
            "averageAutoLoad": 0,
            "averageAutoImprovedLoad": 0,
            "averageAutoImprovement": 0,
            "averageAutoImprovementPercent": 0,
            "averageBehavioralLoad": 0,
            "averageNasaTlxScore": 0,
            "averagePssScore": 0,
            "averagePsqiScore": 0,
            "message": "Auto logs found but required columns are missing.",
        }

    numeric_cols = [
        "cognitiveLoad",
        "improvedLoad",
        "behavioralLoadScore",
        "nasaTlxScore",
        "pssScore",
        "psqiScore",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["cognitiveLoad", "improvedLoad"])

    if df.empty:
        return {
            "totalAutoLogs": 0,
            "averageAutoLoad": 0,
            "averageAutoImprovedLoad": 0,
            "averageAutoImprovement": 0,
            "averageAutoImprovementPercent": 0,
            "averageBehavioralLoad": 0,
            "averageNasaTlxScore": 0,
            "averagePssScore": 0,
            "averagePsqiScore": 0,
            "message": "No valid numeric auto logs found.",
        }

    df["improvement"] = df["cognitiveLoad"] - df["improvedLoad"]

    average_load = df["cognitiveLoad"].mean()
    average_improved = df["improvedLoad"].mean()
    average_improvement = df["improvement"].mean()

    average_improvement_percent = (
        (average_improvement / average_load) * 100 if average_load > 0 else 0
    )

    average_behavioral_load = (
        df["behavioralLoadScore"].mean() if "behavioralLoadScore" in df.columns else 0
    )

    average_nasa_score = (
        df["nasaTlxScore"].mean() if "nasaTlxScore" in df.columns else 0
    )

    average_pss_score = df["pssScore"].mean() if "pssScore" in df.columns else 0
    average_psqi_score = df["psqiScore"].mean() if "psqiScore" in df.columns else 0

    return {
        "totalAutoLogs": int(len(df)),
        "averageAutoLoad": round(average_load, 1),
        "averageAutoImprovedLoad": round(average_improved, 1),
        "averageAutoImprovement": round(average_improvement, 1),
        "averageAutoImprovementPercent": round(average_improvement_percent, 1),
        "averageBehavioralLoad": round(average_behavioral_load, 1),
        "averageNasaTlxScore": round(average_nasa_score, 1),
        "averagePssScore": round(average_pss_score, 1),
        "averagePsqiScore": round(average_psqi_score, 1),
        "message": "Auto logs summarized successfully. These are not counted as valid experiment sessions.",
    }


def analyze_experiment_sessions():
    df = safe_read_csv(EXPERIMENT_LOG_FILE)

    empty_response = {
        "validExperimentSessions": 0,
        "baselineAverageLoad": 0,
        "flowmindAverageLoad": 0,
        "averageReduction": 0,
        "averageReductionPercent": 0,
        "lowRiskSessions": 0,
        "moderateRiskSessions": 0,
        "highRiskSessions": 0,
        "duplicateSessionsIgnored": 0,
        "averageBehavioralLoad": 0,
        "averageNasaTlxScore": 0,
        "averagePssScore": 0,
        "averagePsqiScore": 0,
        "averageFlowmindNasaDifference": 0,
        "flowmindNasaCorrelation": 0,
        "pssNasaCorrelation": 0,
        "psqiNasaCorrelation": 0,
        "behaviorNasaCorrelation": 0,
        "idleNasaCorrelation": 0,
        "backspaceNasaCorrelation": 0,
        "message": "No valid experiment sessions saved yet.",
    }

    if df.empty:
        return empty_response

    original_count = len(df)

    if "sessionId" in df.columns:
        df = df.drop_duplicates(subset=["sessionId"], keep="first")

    duplicate_sessions_ignored = original_count - len(df)

    required_cols = [
        "baselineLoad",
        "flowmindLoad",
        "improvement",
        "improvementPercent",
    ]

    for col in required_cols:
        if col not in df.columns:
            response = empty_response.copy()
            response["duplicateSessionsIgnored"] = duplicate_sessions_ignored
            response["message"] = f"Experiment log missing required column: {col}"
            return response

    numeric_cols = [
        "baselineLoad",
        "flowmindLoad",
        "improvement",
        "improvementPercent",
        "typingSpeed",
        "backspaceCount",
        "idleTime",
        "mouseActivity",
        "behavioralLoadScore",
        "nasaTlxScore",
        "flowmindNasaDifference",
        "pssScore",
        "psqiScore",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=[
            "baselineLoad",
            "flowmindLoad",
            "improvement",
            "improvementPercent",
        ]
    )

    if df.empty:
        response = empty_response.copy()
        response["duplicateSessionsIgnored"] = duplicate_sessions_ignored
        response["message"] = "No valid numeric experiment sessions found."
        return response

    if "risk" in df.columns:
        high_risk = (df["risk"] == "High Overload").sum()
        moderate_risk = (df["risk"] == "Moderate Load").sum()
        low_risk = (df["risk"] == "Low Load").sum()
    else:
        high_risk = 0
        moderate_risk = 0
        low_risk = 0

    average_behavioral_load = (
        df["behavioralLoadScore"].mean() if "behavioralLoadScore" in df.columns else 0
    )

    average_nasa_score = (
        df["nasaTlxScore"].mean() if "nasaTlxScore" in df.columns else 0
    )

    average_pss_score = df["pssScore"].mean() if "pssScore" in df.columns else 0
    average_psqi_score = df["psqiScore"].mean() if "psqiScore" in df.columns else 0

    if "flowmindNasaDifference" in df.columns:
        average_flowmind_nasa_difference = df["flowmindNasaDifference"].mean()
    elif "nasaTlxScore" in df.columns:
        average_flowmind_nasa_difference = (
            df["baselineLoad"] - df["nasaTlxScore"]
        ).abs().mean()
    else:
        average_flowmind_nasa_difference = 0

    if "nasaTlxScore" in df.columns:
        valid_nasa_df = df.dropna(subset=["baselineLoad", "nasaTlxScore"])

        flowmind_nasa_correlation = safe_correlation(
            valid_nasa_df["baselineLoad"],
            valid_nasa_df["nasaTlxScore"],
        )

        behavior_nasa_correlation = (
            safe_correlation(valid_nasa_df["behavioralLoadScore"], valid_nasa_df["nasaTlxScore"])
            if "behavioralLoadScore" in valid_nasa_df.columns
            else 0
        )

        idle_nasa_correlation = (
            safe_correlation(valid_nasa_df["idleTime"], valid_nasa_df["nasaTlxScore"])
            if "idleTime" in valid_nasa_df.columns
            else 0
        )

        backspace_nasa_correlation = (
            safe_correlation(valid_nasa_df["backspaceCount"], valid_nasa_df["nasaTlxScore"])
            if "backspaceCount" in valid_nasa_df.columns
            else 0
        )

        pss_nasa_correlation = (
            safe_correlation(valid_nasa_df["pssScore"], valid_nasa_df["nasaTlxScore"])
            if "pssScore" in valid_nasa_df.columns
            else 0
        )

        psqi_nasa_correlation = (
            safe_correlation(valid_nasa_df["psqiScore"], valid_nasa_df["nasaTlxScore"])
            if "psqiScore" in valid_nasa_df.columns
            else 0
        )
    else:
        flowmind_nasa_correlation = 0
        behavior_nasa_correlation = 0
        idle_nasa_correlation = 0
        backspace_nasa_correlation = 0
        pss_nasa_correlation = 0
        psqi_nasa_correlation = 0

    return {
        "validExperimentSessions": int(len(df)),
        "baselineAverageLoad": round(df["baselineLoad"].mean(), 1),
        "flowmindAverageLoad": round(df["flowmindLoad"].mean(), 1),
        "averageReduction": round(df["improvement"].mean(), 1),
        "averageReductionPercent": round(df["improvementPercent"].mean(), 1),
        "lowRiskSessions": int(low_risk),
        "moderateRiskSessions": int(moderate_risk),
        "highRiskSessions": int(high_risk),
        "duplicateSessionsIgnored": int(duplicate_sessions_ignored),
        "averageBehavioralLoad": round(average_behavioral_load, 1),
        "averageNasaTlxScore": round(average_nasa_score, 1),
        "averagePssScore": round(average_pss_score, 1),
        "averagePsqiScore": round(average_psqi_score, 1),
        "averageFlowmindNasaDifference": round(average_flowmind_nasa_difference, 1),
        "flowmindNasaCorrelation": flowmind_nasa_correlation,
        "pssNasaCorrelation": pss_nasa_correlation,
        "psqiNasaCorrelation": psqi_nasa_correlation,
        "behaviorNasaCorrelation": behavior_nasa_correlation,
        "idleNasaCorrelation": idle_nasa_correlation,
        "backspaceNasaCorrelation": backspace_nasa_correlation,
        "message": "Research-grade experiment validation completed successfully.",
    }


def get_validation_dashboard():
    model_metrics = validate_model()
    auto_log_metrics = analyze_auto_logs()
    experiment_metrics = analyze_experiment_sessions()

    session_metrics = {
        "totalSessions": experiment_metrics["validExperimentSessions"],
        "averageLoad": experiment_metrics["baselineAverageLoad"],
        "averageImprovedLoad": experiment_metrics["flowmindAverageLoad"],
        "averageImprovement": experiment_metrics["averageReduction"],
        "averageImprovementPercent": experiment_metrics["averageReductionPercent"],
        "highRiskSessions": experiment_metrics["highRiskSessions"],
        "moderateRiskSessions": experiment_metrics["moderateRiskSessions"],
        "lowRiskSessions": experiment_metrics["lowRiskSessions"],
        "averageBehavioralLoad": experiment_metrics["averageBehavioralLoad"],
        "averageNasaTlxScore": experiment_metrics["averageNasaTlxScore"],
        "averagePssScore": experiment_metrics["averagePssScore"],
        "averagePsqiScore": experiment_metrics["averagePsqiScore"],
        "averageFlowmindNasaDifference": experiment_metrics["averageFlowmindNasaDifference"],
        "flowmindNasaCorrelation": experiment_metrics["flowmindNasaCorrelation"],
        "pssNasaCorrelation": experiment_metrics["pssNasaCorrelation"],
        "psqiNasaCorrelation": experiment_metrics["psqiNasaCorrelation"],
        "behaviorNasaCorrelation": experiment_metrics["behaviorNasaCorrelation"],
        "idleNasaCorrelation": experiment_metrics["idleNasaCorrelation"],
        "backspaceNasaCorrelation": experiment_metrics["backspaceNasaCorrelation"],
        "message": experiment_metrics["message"],
    }

    return {
        "modelMetrics": model_metrics,
        "autoLogMetrics": auto_log_metrics,
        "experimentMetrics": experiment_metrics,
        "sessionMetrics": session_metrics,
    }


if __name__ == "__main__":
    results = get_validation_dashboard()

    print("Model Metrics:")
    print(results["modelMetrics"])

    print("\nAuto Log Metrics:")
    print(results["autoLogMetrics"])

    print("\nExperiment Metrics:")
    print(results["experimentMetrics"])