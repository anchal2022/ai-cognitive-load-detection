# research_results.py

import os
import pandas as pd
import matplotlib.pyplot as plt

EXPERIMENT_FILE = "experiment_sessions.csv"
OUTPUT_DIR = "../research/research_outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------
# Safe Helpers
# ------------------------------
def safe_numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def safe_correlation(df, col1, col2):
    if col1 not in df.columns or col2 not in df.columns:
        return 0

    temp = df[[col1, col2]].dropna()

    if len(temp) < 2:
        return 0

    if temp[col1].nunique() <= 1 or temp[col2].nunique() <= 1:
        return 0

    corr = temp[col1].corr(temp[col2])

    if pd.isna(corr):
        return 0

    return round(float(corr), 2)


# ------------------------------
# Load Experiment Data
# ------------------------------
if not os.path.exists(EXPERIMENT_FILE):
    print(f"Experiment file not found: {EXPERIMENT_FILE}")
    exit()

df = pd.read_csv(EXPERIMENT_FILE)

if df.empty:
    print("Experiment file is empty.")
    exit()


# ------------------------------
# Clean numeric columns
# ------------------------------
numeric_cols = [
    "tasks",
    "stress",
    "sleep",
    "deadline",
    "postureScore",
    "typingSpeed",
    "backspaceCount",
    "idleTime",
    "mouseActivity",
    "behavioralLoadScore",
    "nasaTlxScore",
    "flowmindNasaDifference",
    "baselineLoad",
    "flowmindLoad",
    "improvement",
    "improvementPercent"
]

df = safe_numeric(df, numeric_cols)

required_cols = [
    "baselineLoad",
    "flowmindLoad",
    "improvement",
    "improvementPercent"
]

df = df.dropna(subset=required_cols)

if df.empty:
    print("No valid numeric experiment sessions found.")
    exit()


# ------------------------------
# Remove duplicate sessions
# ------------------------------
before_count = len(df)

if "sessionId" in df.columns:
    df = df.drop_duplicates(subset=["sessionId"], keep="first")

duplicates_ignored = before_count - len(df)


# ------------------------------
# NASA-TLX and Behavioral Metrics
# ------------------------------
average_behavioral_load = (
    round(df["behavioralLoadScore"].mean(), 2)
    if "behavioralLoadScore" in df.columns
    else 0
)

average_nasa_tlx = (
    round(df["nasaTlxScore"].mean(), 2)
    if "nasaTlxScore" in df.columns
    else 0
)

if "flowmindNasaDifference" in df.columns:
    average_flowmind_nasa_difference = round(df["flowmindNasaDifference"].mean(), 2)
elif "nasaTlxScore" in df.columns:
    average_flowmind_nasa_difference = round(
        (df["baselineLoad"] - df["nasaTlxScore"]).abs().mean(), 2
    )
else:
    average_flowmind_nasa_difference = 0

flowmind_nasa_correlation = safe_correlation(df, "baselineLoad", "nasaTlxScore")
behavior_nasa_correlation = safe_correlation(df, "behavioralLoadScore", "nasaTlxScore")
idle_nasa_correlation = safe_correlation(df, "idleTime", "nasaTlxScore")
backspace_nasa_correlation = safe_correlation(df, "backspaceCount", "nasaTlxScore")


# ------------------------------
# Summary values
# ------------------------------
summary = {
    "Total Valid Experiment Sessions": len(df),
    "Baseline Average Load (%)": round(df["baselineLoad"].mean(), 2),
    "FlowMind Average Load (%)": round(df["flowmindLoad"].mean(), 2),
    "Average Reduction (%)": round(df["improvement"].mean(), 2),
    "Average Reduction Rate (%)": round(df["improvementPercent"].mean(), 2),
    "Low Risk Sessions": int((df["risk"] == "Low Load").sum()) if "risk" in df.columns else 0,
    "Moderate Risk Sessions": int((df["risk"] == "Moderate Load").sum()) if "risk" in df.columns else 0,
    "High Risk Sessions": int((df["risk"] == "High Overload").sum()) if "risk" in df.columns else 0,
    "Average Behavioral Load Score (%)": average_behavioral_load,
    "Average NASA-TLX Score (%)": average_nasa_tlx,
    "Average FlowMind-NASA Difference (%)": average_flowmind_nasa_difference,
    "FlowMind vs NASA-TLX Correlation": flowmind_nasa_correlation,
    "Behavioral Load vs NASA-TLX Correlation": behavior_nasa_correlation,
    "Idle Time vs NASA-TLX Correlation": idle_nasa_correlation,
    "Backspace Count vs NASA-TLX Correlation": backspace_nasa_correlation,
    "Duplicates Ignored": duplicates_ignored
}

summary_df = pd.DataFrame(list(summary.items()), columns=["Metric", "Value"])
summary_df.to_csv(os.path.join(OUTPUT_DIR, "final_results_summary.csv"), index=False)


# ------------------------------
# Clean session table for paper
# ------------------------------
base_columns = [
    "sessionId",
    "tasks",
    "stress",
    "sleep",
    "deadline",
    "postureScore",
    "typingSpeed",
    "backspaceCount",
    "idleTime",
    "mouseActivity",
    "behavioralLoadScore",
    "nasaTlxScore",
    "flowmindNasaDifference",
    "baselineLoad",
    "flowmindLoad",
    "improvement",
    "improvementPercent",
    "risk",
    "topFactor"
]

available_columns = [col for col in base_columns if col in df.columns]
clean_table = df[available_columns]

clean_table.to_csv(os.path.join(OUTPUT_DIR, "clean_experiment_sessions.csv"), index=False)


# ------------------------------
# Figure 1: Baseline vs FlowMind Average Load
# ------------------------------
plt.figure(figsize=(7, 5))
plt.bar(
    ["Baseline Avg Load", "FlowMind Avg Load"],
    [
        summary["Baseline Average Load (%)"],
        summary["FlowMind Average Load (%)"]
    ]
)
plt.ylabel("Cognitive Load (%)")
plt.title("Baseline vs FlowMind Average Cognitive Load")
plt.ylim(0, 100)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "figure_baseline_vs_flowmind.png"), dpi=300)
plt.close()


# ------------------------------
# Figure 2: Risk Distribution
# ------------------------------
if "risk" in df.columns:
    risk_counts = df["risk"].value_counts()

    plt.figure(figsize=(7, 5))
    plt.bar(risk_counts.index, risk_counts.values)
    plt.ylabel("Number of Sessions")
    plt.title("Risk Distribution Across Experiment Sessions")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "figure_risk_distribution.png"), dpi=300)
    plt.close()


# ------------------------------
# Figure 3: Session-wise Reduction
# ------------------------------
plt.figure(figsize=(10, 5))
plt.plot(range(1, len(df) + 1), df["improvementPercent"], marker="o")
plt.xlabel("Experiment Session")
plt.ylabel("Reduction Rate (%)")
plt.title("Session-wise Cognitive Load Reduction")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "figure_session_wise_reduction.png"), dpi=300)
plt.close()


# ------------------------------
# Figure 4: Main Overload Driver Frequency
# ------------------------------
if "topFactor" in df.columns:
    top_factor_counts = df["topFactor"].value_counts()

    plt.figure(figsize=(7, 5))
    plt.bar(top_factor_counts.index, top_factor_counts.values)
    plt.ylabel("Frequency")
    plt.title("Main Overload Driver Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "figure_top_factor_frequency.png"), dpi=300)
    plt.close()


# ------------------------------
# Figure 5: FlowMind vs NASA-TLX
# ------------------------------
if "nasaTlxScore" in df.columns:
    nasa_df = df.dropna(subset=["baselineLoad", "nasaTlxScore"])

    if not nasa_df.empty:
        plt.figure(figsize=(8, 5))
        plt.plot(range(1, len(nasa_df) + 1), nasa_df["baselineLoad"], marker="o", label="FlowMind Score")
        plt.plot(range(1, len(nasa_df) + 1), nasa_df["nasaTlxScore"], marker="s", label="NASA-TLX Score")
        plt.xlabel("Experiment Session")
        plt.ylabel("Workload Score (%)")
        plt.title("FlowMind Score vs NASA-TLX Score")
        plt.ylim(0, 100)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "figure_flowmind_vs_nasa_tlx.png"), dpi=300)
        plt.close()


# ------------------------------
# Figure 6: Behavioral Load vs NASA-TLX
# ------------------------------
if "behavioralLoadScore" in df.columns and "nasaTlxScore" in df.columns:
    behavior_df = df.dropna(subset=["behavioralLoadScore", "nasaTlxScore"])

    if not behavior_df.empty:
        plt.figure(figsize=(7, 5))
        plt.scatter(behavior_df["behavioralLoadScore"], behavior_df["nasaTlxScore"])
        plt.xlabel("Behavioral Load Score (%)")
        plt.ylabel("NASA-TLX Score (%)")
        plt.title("Behavioral Load Score vs NASA-TLX Score")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "figure_behavior_vs_nasa_tlx.png"), dpi=300)
        plt.close()


# ------------------------------
# Figure 7: Behavioral Feature Averages
# ------------------------------
behavior_cols = [
    "typingSpeed",
    "backspaceCount",
    "idleTime",
    "mouseActivity",
    "behavioralLoadScore"
]

available_behavior_cols = [col for col in behavior_cols if col in df.columns]

if available_behavior_cols:
    behavior_avg = df[available_behavior_cols].mean()

    plt.figure(figsize=(8, 5))
    plt.bar(behavior_avg.index, behavior_avg.values)
    plt.ylabel("Average Value")
    plt.title("Average Behavioral Feature Values")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "figure_behavioral_feature_summary.png"), dpi=300)
    plt.close()


# ------------------------------
# Correlation Table
# ------------------------------
correlation_summary = {
    "Correlation Metric": [
        "FlowMind Score vs NASA-TLX",
        "Behavioral Load vs NASA-TLX",
        "Idle Time vs NASA-TLX",
        "Backspace Count vs NASA-TLX"
    ],
    "Correlation Value": [
        flowmind_nasa_correlation,
        behavior_nasa_correlation,
        idle_nasa_correlation,
        backspace_nasa_correlation
    ]
}

correlation_df = pd.DataFrame(correlation_summary)
correlation_df.to_csv(os.path.join(OUTPUT_DIR, "nasa_behavior_correlation_summary.csv"), index=False)


# ------------------------------
# Final Output
# ------------------------------
print("Research outputs generated successfully.")
print("Files saved inside:", OUTPUT_DIR)

print("\nFinal Summary:")
print(summary_df)

print("\nCorrelation Summary:")
print(correlation_df)