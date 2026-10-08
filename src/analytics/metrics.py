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
from scipy import stats as scipy_stats

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.simulation.simulate import run_simulation, NUM_DRIVERS, SIM_DURATION_MIN

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
FIGURES_DIR = Path(__file__).resolve().parents[2] / "outputs" / "figures"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "outputs" / "reports"


def compute_kpis(df: pd.DataFrame, num_drivers: int, sim_duration_min: int) -> dict:
    total = len(df)
    if total == 0:
        # Zero demand (or a configuration that happened to generate no requests):
        # return a well-formed all-zero result instead of dividing by zero.
        return {
            "total_requests": 0,
            "completion_rate_pct": 0.0,
            "driver_cancellation_rate_pct": 0.0,
            "customer_cancellation_rate_pct": 0.0,
            "no_driver_found_rate_pct": 0.0,
            "incomplete_rate_pct": 0.0,
            "avg_wait_time_min": 0.0,
            "avg_trip_duration_min": 0.0,
            "avg_trip_distance_km": 0.0,
            "driver_utilization_pct": 0.0,
            "avg_driver_idle_time_min": float(sim_duration_min),
        }
    counts = df["status"].value_counts()

    # Driver utilization: sum up how many minutes drivers were occupied
    # (wait_time covers assignment->pickup; trip_duration covers the trip itself, if it happened)
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


def validate_distributions(sim_df: pd.DataFrame) -> dict:
    """
    Kolmogorov-Smirnov test comparing simulated vs real distributions for
    wait time, trip duration, and trip distance. This is the quantitative
    version of your Success Criteria's "reasonable similarity" requirement --
    rather than eyeballing histograms, this gives a statistic + p-value.

    IMPORTANT CAVEAT (include this in your report): with a large sample size
    (thousands of rides), the KS test becomes extremely sensitive and will
    often report a "statistically significant difference" (p < 0.05) even
    when the two distributions look nearly identical on a chart. This is a
    known property of KS testing at scale, not a sign your simulation is
    broken. The KS *statistic* itself (D) is the more useful number here:
    it's the maximum gap between the two cumulative distributions, and
    roughly speaking, D < 0.1 is a strong match, D < 0.2 is reasonable,
    D > 0.3 suggests a real mismatch worth investigating.
    """
    reference_df = pd.read_csv(PROCESSED_DIR / "ncr_rides_cleaned.csv")

    comparisons = {
        "wait_time_vs_VTAT": (
            sim_df["wait_time"].dropna(), reference_df["Avg VTAT"].dropna()
        ),
        "trip_duration_vs_CTAT": (
            sim_df["trip_duration"].dropna(), reference_df["Avg CTAT"].dropna()
        ),
        "distance_vs_RideDistance": (
            sim_df["distance"].dropna(), reference_df["Ride Distance"].dropna()
        ),
    }

    results = {}
    for name, (sim_values, real_values) in comparisons.items():
        if len(sim_values) < 2 or len(real_values) < 2:
            results[name] = {"statistic": None, "p_value": None, "verdict": "insufficient data"}
            continue

        ks_stat, p_value = scipy_stats.ks_2samp(sim_values, real_values)

        if ks_stat < 0.1:
            verdict = "strong match"
        elif ks_stat < 0.2:
            verdict = "reasonable match"
        else:
            verdict = "notable mismatch -- investigate"

        results[name] = {
            "statistic": round(float(ks_stat), 4),
            "p_value": round(float(p_value), 6),
            "verdict": verdict,
        }

    return results


def print_validation(results: dict):
    print("\n=== Statistical Validation (Kolmogorov-Smirnov test) ===")
    for name, r in results.items():
        print(f"  {name}: D={r['statistic']}, p={r['p_value']} -> {r['verdict']}")
    print("\n  Note: with large n, KS p-values are often < 0.05 even for close")
    print("  distributions. Judge fit by the D statistic (max CDF gap), not p alone.")


def save_validation_report(results: dict, filename="statistical_validation.txt") -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / filename
    lines = ["Statistical Validation -- Kolmogorov-Smirnov Test", "=" * 50]
    for name, r in results.items():
        lines.append(f"{name}: D={r['statistic']}, p={r['p_value']} -> {r['verdict']}")
    lines.append("")
    lines.append("Caveat: with large sample sizes, KS p-values are often significant")
    lines.append("(p < 0.05) even when distributions are visually very close. The D")
    lines.append("statistic (max gap between cumulative distributions) is the more")
    lines.append("informative number: D < 0.1 strong match, D < 0.2 reasonable, D > 0.3")
    lines.append("suggests a real mismatch worth investigating further.")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Validation report saved: {path}")
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

    validation_results = validate_distributions(df)
    print_validation(validation_results)
    save_validation_report(validation_results)


if __name__ == "__main__":
    main()