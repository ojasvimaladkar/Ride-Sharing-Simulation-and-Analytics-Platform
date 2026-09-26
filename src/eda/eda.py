"""
Exploratory Data Analysis Module
----------------------------------
- Ride demand by time period (hourly/daily/peak vs non-peak)
- Booking status / outcome breakdown
- Pickup/drop location patterns
- Trip distance and duration distributions
- Cancellation pattern analysis
Outputs figures to outputs/figures/ and a text summary to outputs/reports/.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
FIGURES_DIR = Path(__file__).resolve().parents[2] / "outputs" / "figures"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "outputs" / "reports"


def load_clean_data() -> pd.DataFrame:
    path = PROCESSED_DIR / "ncr_rides_cleaned.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run preprocess.py first.")
    df = pd.read_csv(path, parse_dates=["datetime"])
    print(f"Loaded {len(df)} cleaned rows")
    return df


def outcome_breakdown(df: pd.DataFrame) -> pd.Series:
    counts = df["Booking Status"].value_counts()
    pct = (counts / len(df) * 100).round(2)
    summary = pd.DataFrame({"count": counts, "pct": pct})
    print("\n=== Ride Outcome Breakdown ===")
    print(summary.to_string())

    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind="bar", ax=ax, color="#4C72B0")
    ax.set_title("Ride Outcomes")
    ax.set_ylabel("Number of Rides")
    ax.set_xlabel("Booking Status")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "outcome_breakdown.png", dpi=150)
    plt.close(fig)

    return counts


def demand_by_hour(df: pd.DataFrame) -> pd.Series:
    hourly = df.groupby("hour").size()
    peak_hour = hourly.idxmax()
    print(f"\n=== Demand by Hour ===\nPeak hour: {peak_hour}:00 ({hourly.max()} rides)")

    fig, ax = plt.subplots(figsize=(10, 5))
    hourly.plot(kind="line", marker="o", ax=ax, color="#DD8452")
    ax.set_title("Ride Demand by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Number of Rides")
    ax.set_xticks(range(0, 24))
    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "demand_by_hour.png", dpi=150)
    plt.close(fig)

    return hourly


def demand_by_day(df: pd.DataFrame) -> pd.Series:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily = df.groupby("day_of_week").size().reindex(order)
    print("\n=== Demand by Day of Week ===")
    print(daily.to_string())

    fig, ax = plt.subplots(figsize=(9, 5))
    daily.plot(kind="bar", ax=ax, color="#55A868")
    ax.set_title("Ride Demand by Day of Week")
    ax.set_ylabel("Number of Rides")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "demand_by_day.png", dpi=150)
    plt.close(fig)

    return daily


def trip_distance_duration(df: pd.DataFrame) -> None:
    completed = df[df["is_completed"]]
    print(f"\n=== Trip Distance / Duration (completed rides only, n={len(completed)}) ===")
    print(completed[["Ride Distance", "Avg CTAT"]].describe().to_string())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    completed["Ride Distance"].dropna().plot(kind="hist", bins=40, ax=axes[0], color="#8172B2")
    axes[0].set_title("Ride Distance Distribution (km)")
    axes[0].set_xlabel("Distance (km)")

    completed["Avg CTAT"].dropna().plot(kind="hist", bins=40, ax=axes[1], color="#C44E52")
    axes[1].set_title("Trip Duration Distribution (Avg CTAT, min)")
    axes[1].set_xlabel("Duration (min)")

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "distance_duration_distribution.png", dpi=150)
    plt.close(fig)


def cancellation_reasons(df: pd.DataFrame) -> None:
    print("\n=== Customer Cancellation Reasons ===")
    print(df["Reason for cancelling by Customer"].value_counts().to_string())

    print("\n=== Driver Cancellation Reasons ===")
    print(df["Driver Cancellation Reason"].value_counts().to_string())


def vehicle_type_breakdown(df: pd.DataFrame) -> None:
    print("\n=== Bookings by Vehicle Type ===")
    print(df["Vehicle Type"].value_counts().to_string())

    completion_by_vehicle = df.groupby("Vehicle Type")["is_completed"].mean().sort_values(ascending=False) * 100
    print("\n=== Completion Rate by Vehicle Type (%) ===")
    print(completion_by_vehicle.round(2).to_string())


def write_summary_report(df: pd.DataFrame, outcome_counts: pd.Series) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "eda_summary.txt"

    total = len(df)
    completed_pct = (outcome_counts.get("Completed", 0) / total) * 100
    cust_cancel_pct = (outcome_counts.get("Cancelled by Customer", 0) / total) * 100
    driver_cancel_pct = (outcome_counts.get("Cancelled by Driver", 0) / total) * 100
    no_driver_pct = (outcome_counts.get("No Driver Found", 0) / total) * 100
    incomplete_pct = (outcome_counts.get("Incomplete", 0) / total) * 100

    lines = [
        "EDA Summary — NCR Ride-Sharing Dataset",
        "=" * 45,
        f"Total bookings: {total:,}",
        "",
        "Ride Outcome Breakdown:",
        f"  Completed:              {completed_pct:.2f}%",
        f"  Cancelled by Driver:    {driver_cancel_pct:.2f}%",
        f"  Cancelled by Customer:  {cust_cancel_pct:.2f}%",
        f"  No Driver Found:        {no_driver_pct:.2f}%",
        f"  Incomplete:             {incomplete_pct:.2f}%",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSummary report saved: {report_path}")


def run():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = load_clean_data()

    outcome_counts = outcome_breakdown(df)
    demand_by_hour(df)
    demand_by_day(df)
    trip_distance_duration(df)
    cancellation_reasons(df)
    vehicle_type_breakdown(df)
    write_summary_report(df, outcome_counts)

    print(f"\nAll figures saved to: {FIGURES_DIR}")


if __name__ == "__main__":
    run()