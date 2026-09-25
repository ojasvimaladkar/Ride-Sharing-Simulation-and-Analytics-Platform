"""
Ride-Sharing Simulation (simplified, single file)
-----------------------------------------------------
1. Loads the cleaned dataset and computes a few basic averages
2. Runs a SimPy simulation: requests arrive -> try to get a driver ->
   possible cancellation -> trip -> done
3. Returns results as a DataFrame (run_simulation), and when run directly,
   prints outcome counts and saves the results to CSV
"""

import random
import pandas as pd
import simpy
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "outputs" / "reports"

# ----- Default simulation settings -----
NUM_DRIVERS = 9
SIM_DURATION_MIN = 24 * 60      # simulate one day
MAX_WAIT_FOR_DRIVER_MIN = 15    # how long a request waits before giving up
RANDOM_SEED = 42


def load_stats():
    """Loads the cleaned dataset and computes the numbers the simulation needs."""
    df = pd.read_csv(PROCESSED_DIR / "ncr_rides_cleaned.csv")

    n_days = df["date_only"].nunique() if "date_only" in df.columns else 1
    avg_daily_requests = len(df) / max(n_days, 1)

    avg_vtat = df["Avg VTAT"].dropna().mean()
    avg_ctat = df["Avg CTAT"].dropna().mean()
    avg_distance = df["Ride Distance"].dropna().mean()

    status_counts = df["Booking Status"].value_counts()
    total = len(df)
    n_no_driver = status_counts.get("No Driver Found", 0)
    n_assigned = total - n_no_driver

    p_customer_cancel = status_counts.get("Cancelled by Customer", 0) / n_assigned
    p_driver_cancel = status_counts.get("Cancelled by Driver", 0) / n_assigned

    n_completed = status_counts.get("Completed", 0)
    n_incomplete = status_counts.get("Incomplete", 0)
    p_incomplete = n_incomplete / (n_completed + n_incomplete)

    # Pickup/drop locations and vehicle types, with real frequencies, for synthetic output
    pickup_locations = df["Pickup Location"].dropna().unique().tolist()
    drop_locations = df["Drop Location"].dropna().unique().tolist()
    vehicle_types = df["Vehicle Type"].value_counts(normalize=True)

    return {
        "avg_daily_requests": avg_daily_requests,
        "avg_vtat": avg_vtat,
        "avg_ctat": avg_ctat,
        "avg_distance": avg_distance,
        "p_customer_cancel": p_customer_cancel,
        "p_driver_cancel": p_driver_cancel,
        "p_incomplete": p_incomplete,
        "pickup_locations": pickup_locations,
        "drop_locations": drop_locations,
        "vehicle_types": vehicle_types.index.tolist(),
        "vehicle_type_weights": vehicle_types.values.tolist(),
    }


def handle_request(env, request_id, drivers, stats, results):
    """One ride request, from arrival to completion/cancellation."""
    vehicle_type = random.choices(stats["vehicle_types"], weights=stats["vehicle_type_weights"], k=1)[0]
    pickup = random.choice(stats["pickup_locations"])
    drop = random.choice(stats["drop_locations"])
    hour = int((env.now // 60) % 24)

    base_record = {
        "ride_id": request_id, "hour": hour, "vehicle_type": vehicle_type,
        "pickup_location": pickup, "drop_location": drop,
    }

    with drivers.request() as req:
        got_driver = yield req | env.timeout(MAX_WAIT_FOR_DRIVER_MIN)

        if req not in got_driver:
            results.append({**base_record, "status": "No Driver Found",
                             "wait_time": None, "trip_duration": None, "distance": None})
            return

        yield env.timeout(stats["avg_vtat"])

        if random.random() < stats["p_customer_cancel"]:
            results.append({**base_record, "status": "Cancelled by Customer",
                             "wait_time": stats["avg_vtat"], "trip_duration": None, "distance": None})
            return

        if random.random() < stats["p_driver_cancel"]:
            results.append({**base_record, "status": "Cancelled by Driver",
                             "wait_time": stats["avg_vtat"], "trip_duration": None, "distance": None})
            return

        yield env.timeout(stats["avg_ctat"])

        status = "Incomplete" if random.random() < stats["p_incomplete"] else "Completed"
        results.append({**base_record, "status": status,
                         "wait_time": stats["avg_vtat"], "trip_duration": stats["avg_ctat"],
                         "distance": stats["avg_distance"]})


def request_arrivals(env, drivers, stats, results, demand_multiplier):
    """Generates ride requests at a steady average rate all day."""
    rate_per_min = (stats["avg_daily_requests"] * demand_multiplier) / (24 * 60)
    request_id = 0

    while True:
        yield env.timeout(random.expovariate(rate_per_min))
        request_id += 1
        env.process(handle_request(env, request_id, drivers, stats, results))


def run_simulation(num_drivers=NUM_DRIVERS, demand_multiplier=1.0,
                    sim_duration_min=SIM_DURATION_MIN, seed=RANDOM_SEED,
                    stats=None):
    """
    Runs one simulation and returns (results_df, stats).
    Reusable by scenarios/what_if.py with different num_drivers / demand_multiplier.
    """
    random.seed(seed)
    if stats is None:
        stats = load_stats()

    env = simpy.Environment()
    drivers = simpy.Resource(env, capacity=num_drivers)
    results = []

    env.process(request_arrivals(env, drivers, stats, results, demand_multiplier))
    env.run(until=sim_duration_min)

    df = pd.DataFrame(results)
    return df, stats


def run():
    """Runs the default baseline scenario, prints a summary, and saves the CSV."""
    df, stats = run_simulation()

    print("=== Stats from dataset ===")
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")

    print(f"\n=== Simulation done: {len(df)} requests over {SIM_DURATION_MIN} minutes, {NUM_DRIVERS} drivers ===")
    counts = df["status"].value_counts()
    for status, count in counts.items():
        print(f"  {status}: {count} ({count / len(df) * 100:.1f}%)")

    completed = df[df["status"] == "Completed"]
    print(f"\nAvg wait time (assigned rides): {df['wait_time'].dropna().mean():.1f} min")
    print(f"Avg trip duration (completed): {completed['trip_duration'].mean():.1f} min")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "simulation_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved results: {out_path}")

    return df, stats


if __name__ == "__main__":
    run()