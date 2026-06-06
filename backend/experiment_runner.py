# experiment_runner.py

import pandas as pd
from plot_utils import plot_cognitive_load_bar

LOG_FILE = "user_metrics.csv"

def run_experiments():
    df = pd.read_csv(LOG_FILE)
    baseline = df["cognitiveLoad"].mean()
    optimized = df["improvedLoad"].mean()
    reduction = baseline - optimized
    print(f"Baseline Avg Load: {baseline:.2f}")
    print(f"Optimized Avg Load: {optimized:.2f}")
    print(f"Average Reduction: {reduction:.2f}")

    # Plot bar chart for experiment
    plot_cognitive_load_bar()

if __name__ == "__main__":
    run_experiments()