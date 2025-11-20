import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_report():
    results_path = "reports/benchmark_results.csv"
    if not os.path.exists(results_path):
        print(f"No results found at {results_path}. Run benchmarks first.")
        return

    df = pd.read_csv(results_path)
    
    # Set style
    sns.set_theme(style="whitegrid")
    
    # Create a figure with subplots
    scenarios = df["scenario"].unique()
    fig, axes = plt.subplots(1, len(scenarios), figsize=(15, 6))
    
    if len(scenarios) == 1:
        axes = [axes]

    for i, scenario in enumerate(scenarios):
        scenario_data = df[df["scenario"] == scenario]
        
        sns.barplot(
            data=scenario_data, 
            x="protocol", 
            y="latency_ms", 
            ax=axes[i], 
            capsize=.1, 
            errorbar="sd",
            palette="viridis"
        )
        
        axes[i].set_title(f"{scenario} Latency")
        axes[i].set_ylabel("Latency (ms)")
        axes[i].set_xlabel("Protocol")

    plt.tight_layout()
    output_path = "reports/latency_comparison.png"
    plt.savefig(output_path)
    print(f"Report generated: {output_path}")

if __name__ == "__main__":
    generate_report()
