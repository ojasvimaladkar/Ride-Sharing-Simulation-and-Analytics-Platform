"""
Scenario Analysis Module
----------------------------
Runs the simulation under different driver-supply and demand-level
combinations, and compares KPIs across them (your proposal's "what-if" feature).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.simulation.simulate import run_simulation, SIM_DURATION_MIN
from src.analytics.metrics import compute_kpis

REPORTS_DIR = Path(__file__).resolve().parents[2] / "outputs" / "reports"
FIGURES_DIR = Path(__file__).resolve().parents[2] / "outputs" / "figures"

# ----- Scenarios to compare: (label, num_drivers, demand_multiplier) -----
SCENARIOS = [
    ("Baseline (25 drivers, normal demand)", 25, 1.0),
    ("Low driver supply (18 drivers)", 18, 1.0),
    ("High driver supply (35 drivers)", 35, 1.0),
    ("Increased demand (+30%, 25 drivers)", 25, 1.3),
    ("Reduced demand (-30%, 25 drivers)", 25, 0.7),
    ("Zero demand (25 drivers, 0 demand)", 25, 0.0),
]


def run_all_scenarios():
    shared_stats = None
    rows = []

    for label, num_drivers, demand_multiplier in SCENARIOS:
        df, shared_stats = run_simulation(
            num_drivers=num_drivers, demand_multiplier=demand_multiplier,
            stats=shared_stats,
        )
        kpis = compute_kpis(df, num_drivers, SIM_DURATION_MIN)
        kpis["scenario"] = label
        kpis["num_drivers"] = num_drivers
        kpis["demand_multiplier"] = demand_multiplier
        rows.append(kpis)

        print(f"\n--- {label} ---")
        print(f"  Requests: {kpis['total_requests']}  |  "
              f"Completed: {kpis['completed_rides']} ({kpis['completion_rate_pct']:.1f}%)  |  "
              f"Revenue: INR {kpis['total_revenue']:,.0f}  |  "
              f"Utilization: {kpis['driver_utilization_pct']:.1f}%  |  "
              f"Avg wait: {kpis['avg_wait_time_min']:.1f} min")

    return pd.DataFrame(rows)


def save_comparison_table(comparison_df: pd.DataFrame) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "scenario_comparison.csv"
    comparison_df.to_csv(path, index=False)
    print(f"\nScenario comparison saved: {path}")
    return path


def plot_scenario_comparison(comparison_df: pd.DataFrame):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    comparison_df.plot(x="scenario", y=["total_requests", "completed_rides"], kind="bar",
                        ax=axes[0], color=["#4C72B0", "#55A868"])
    axes[0].set_title("Total Requests vs. Completed Rides")
    axes[0].set_ylabel("Count")
    axes[0].set_xlabel("")
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].legend(["Requests", "Completed"])

    comparison_df.plot(x="scenario", y=["completion_rate_pct", "driver_utilization_pct"], kind="bar",
                        ax=axes[1], color=["#55A868", "#F2A93B"])
    axes[1].set_title("Completion Rate & Driver Utilization")
    axes[1].set_ylabel("%")
    axes[1].set_xlabel("")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].legend(["Completion %", "Utilization %"])

    comparison_df.plot(x="scenario", y="avg_wait_time_min", kind="bar",
                        ax=axes[2], color="#C44E52", legend=False)
    axes[2].set_title("Avg Wait Time by Scenario")
    axes[2].set_ylabel("Minutes")
    axes[2].set_xlabel("")
    axes[2].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    out_path = FIGURES_DIR / "scenario_comparison.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved scenario comparison chart: {out_path}")


def main():
    comparison_df = run_all_scenarios()
    save_comparison_table(comparison_df)
    plot_scenario_comparison(comparison_df)


if __name__ == "__main__":
    main()