"""
Analytics and Visualization Module
--------------------------------------
Computes operational KPIs from a simulation run and creates the
simulated-vs-reference comparison chart (your Success Criteria check).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.simulation.simulate import run_simulation, NUM_DRIVERS, SIM_DURATION_MIN

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
FIGURES_DIR = Path(__file__).resolve().parents[2] / "outputs" / "figures"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "outputs" / "reports"


def compute_kpis(df: pd.DataFrame, num_drivers: int, sim_duration_min: int) -> dict:
    total = len(df)
    counts = df["status"].value_counts()

    occupied_time = df["wait_time"].fillna(0) + df["trip_duration"].fillna(0)
    total_busy_minutes = occupied_time.sum()
    total_available_minutes = num_drivers * sim_duration_min

    utilization_pct = total_busy_minutes / total_available_minutes * 100
    avg_idle_min = sim_duration_min - (total_busy_minutes / num_drivers)

    return {
        "total_requests": total,
        "completion_rate_pct": counts.get("Completed", 0) / total * 100,
        "driver_cancellation_rate_pct": counts.get("Cancelled by Driver", 0) / total * 100,
        "customer_cancellation_rate_pct": counts.get("Cancelled by Customer", 0) / total * 100,
        "no_driver_found_rate_pct": counts.get("No Driver Found", 0) / total * 100,
        "incomplete_rate_pct": counts.get("Incomplete", 0) / total * 100,
        "avg_wait_time_min": df["wait_time"].dropna().mean(),
        "avg_trip_duration_min": df["trip_duration"].dropna().mean(),
        "avg_trip_distance_km": df["distance"].dropna().mean(),
        "driver_utilization_pct": utilization_pct,
        "avg_driver_idle_time_min": avg_idle_min,
    }


def print_kpis(kpis: dict):
    print("\n=== Simulation KPIs ===")
    for k, v in kpis.items():
        print(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")


def save_kpi_report(kpis: dict, filename="simulation_kpis.txt") -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / filename
    lines = ["Simulation KPI Report", "=" * 30]
    for k, v in kpis.items():
        lines.append(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nKPI report saved: {path}")
    return path


def plot_outcome_comparison(sim_df: pd.DataFrame):
    """The core validation chart: simulated outcome % vs real dataset outcome %."""
    reference_df = pd.read_csv(PROCESSED_DIR / "ncr_rides_cleaned.csv")

    sim_pct = sim_df["status"].value_counts(normalize=True) * 100
    ref_pct = reference_df["Booking Status"].value_counts(normalize=True) * 100

    compare = pd.DataFrame({"Simulated": sim_pct, "Real Dataset": ref_pct}).fillna(0)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    compare.plot(kind="bar", ax=ax, color=["#4C72B0", "#DD8452"])
    ax.set_title("Simulated vs Real: Ride Outcome Distribution")
    ax.set_ylabel("% of Rides")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    out_path = FIGURES_DIR / "sim_vs_real_outcomes.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved comparison chart: {out_path}")


def main():
    df, stats = run_simulation()
    kpis = compute_kpis(df, NUM_DRIVERS, SIM_DURATION_MIN)
    print_kpis(kpis)
    save_kpi_report(kpis)
    plot_outcome_comparison(df)


if __name__ == "__main__":
    main()