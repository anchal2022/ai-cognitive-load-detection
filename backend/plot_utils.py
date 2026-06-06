# plot_utils.py

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

LOG_FILE = "user_metrics.csv"

def plot_cognitive_load_bar():
    df = pd.read_csv(LOG_FILE)
    plt.figure(figsize=(8,6))
    plt.bar(df.index, df["cognitiveLoad"], color='tomato', label="Cognitive Load")
    plt.bar(df.index, df["improvedLoad"], color='green', alpha=0.6, label="Improved Load")
    plt.xlabel("Sample Index")
    plt.ylabel("Cognitive Load (%)")
    plt.title("Cognitive Load vs AI-Improved Load")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_attention_heatmap():
    df = pd.read_csv(LOG_FILE)
    heatmap_data = df[["cognitiveLoad", "improvedLoad"]].T
    plt.figure(figsize=(10,4))
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlOrRd")
    plt.title("Attention / Cognitive Load Heatmap")
    plt.show()

if __name__ == "__main__":
    plot_cognitive_load_bar()
    plot_attention_heatmap()