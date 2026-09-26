"""
Ride-Sharing Simulation (vehicle-type-aware matching + time-varying driver supply)
---------------------------------------------------------------------------------------
1. Loads the cleaned dataset and computes averages + distributions
2. Splits the driver fleet into per-vehicle-type pools, sized proportionally to
   real vehicle-type demand
3. Within each pool, driver SUPPLY also varies by hour: fewer drivers are
   "on shift" overnight, more during peak hours -- modeled via non-blocking
   "phantom driver" holds that occupy fleet slots during low-demand hours and
   release them as real demand rises, without ever interrupting a ride in
   progress (see ShiftController / PhantomDriver below)
4. Runs a SimPy simulation and returns results as a DataFrame
"""

import random
import pandas as pd
import simpy
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "outputs" / "reports"

NUM_DRIVERS = 20
SIM_DURATION_MIN = 24 * 60
MAX_WAIT_FOR_DRIVER_MIN = 15
RANDOM_SEED = 42
MIN_ACTIVE_FRACTION = 0.5   # even at the quietest hour, at least this fraction of the fleet is on shift
ENABLE_SHIFT_DYNAMICS = True  # set False to go back to a flat fleet all day


def load_stats():
    """Loads the cleaned dataset and computes the numbers the simulation needs."""
    df = pd.read_csv(PROCESSED_DIR / "ncr_rides_cleaned.csv")

    n_days = df["date_only"].nunique() if "date_only" in df.columns else 1
    avg_daily_requests = len(df) / max(n_days, 1)

    vtat_samples = df["Avg VTAT"].dropna().tolist()
    ctat_samples = df["Avg CTAT"].dropna().tolist()
    distance_samples = df["Ride Distance"].dropna().tolist()

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

    pickup_locations = df["Pickup Location"].dropna().unique().tolist()
    drop_locations = df["Drop Location"].dropna().unique().tolist()
    vehicle_types = df["Vehicle Type"].value_counts(normalize=True)

    hourly_counts = df["hour"].value_counts().reindex(range(24), fill_value=0)
    hourly_weights = (hourly_counts / hourly_counts.sum()).to_dict()

    return {
        "avg_daily_requests": avg_daily_requests,
        "vtat_samples": vtat_samples,
        "ctat_samples": ctat_samples,
        "distance_samples": distance_samples,
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
        "hourly_weights": hourly_weights,
    }


def allocate_driver_pools(num_drivers: int, vehicle_types: list, vehicle_type_weights: list) -> dict:
    """Splits num_drivers across vehicle types proportionally, largest-remainder rounding."""
    raw = [w * num_drivers for w in vehicle_type_weights]
    floors = [int(x) for x in raw]
    remainder = num_drivers - sum(floors)

    remainders = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in remainders[:remainder]:
        floors[i] += 1

    return dict(zip(vehicle_types, floors))


class PhantomDriver:
    """
    Represents an off-shift driver: holds one fleet slot (at high priority,
    so it's claimed ahead of waiting ride requests as slots free up) until
    told to stop. Never interrupts a ride already in progress -- it only
    claims a slot once it's actually free.
    """
    def __init__(self, env, pool):
        self.env = env
        self.pool = pool
        self._stop = env.event()
        env.process(self._run())

    def _run(self):
        with self.pool.request(priority=0) as req:
            yield req
            yield self._stop

    def stop(self):
        if not self._stop.triggered:
            self._stop.succeed()


class ShiftController:
    """
    Per-vehicle-type-pool controller that adjusts how many PhantomDrivers are
    "holding a slot off-shift" each hour, based on that hour's share of real
    demand. Peak hour -> full fleet active. Quietest hour -> MIN_ACTIVE_FRACTION
    of the fleet active. Runs as a background SimPy process for the whole sim.
    """
    def __init__(self, env, pool, capacity, hourly_weights, min_active_fraction):
        self.env = env
        self.pool = pool
        self.capacity = capacity
        self.hourly_weights = hourly_weights
        self.min_active_fraction = min_active_fraction
        self.max_weight = max(hourly_weights.values()) if hourly_weights else (1 / 24)
        self.phantoms = []
        env.process(self._run())

    def _target_off_duty(self, hour):
        weight = self.hourly_weights.get(hour, 1 / 24)
        active_fraction = self.min_active_fraction + (1 - self.min_active_fraction) * (weight / self.max_weight)
        active_count = round(self.capacity * active_fraction)
        return max(self.capacity - active_count, 0)

    def _run(self):
        current_hour = -1
        while True:
            hour = int((self.env.now // 60) % 24)
            if hour != current_hour:
                current_hour = hour
                target = self._target_off_duty(hour)
                current = len(self.phantoms)

                if target > current:
                    for _ in range(target - current):
                        self.phantoms.append(PhantomDriver(self.env, self.pool))
                elif target < current:
                    for _ in range(current - target):
                        self.phantoms.pop().stop()

            yield self.env.timeout(1)


def handle_request(env, request_id, driver_pools, driver_counters, stats, results):
    """One ride request, matched only to a driver of the SAME vehicle type."""
    vehicle_type = random.choices(stats["vehicle_types"], weights=stats["vehicle_type_weights"], k=1)[0]
    pickup = random.choice(stats["pickup_locations"])
    drop = random.choice(stats["drop_locations"])
    hour = int((env.now // 60) % 24)
    request_time_min = round(env.now, 2)
    rider_id = f"RIDER-{request_id:05d}"

    base_record = {
        "ride_id": request_id, "rider_id": rider_id, "driver_id": None,
        "request_time_min": request_time_min, "hour": hour, "vehicle_type": vehicle_type,
        "pickup_location": pickup, "drop_location": drop,
    }

    pool = driver_pools.get(vehicle_type)
    if pool is None:
        results.append({**base_record, "status": "No Driver Found",
                         "wait_time": None, "trip_duration": None, "distance": None})
        return

    with pool.request(priority=10) as req:
        got_driver = yield req | env.timeout(MAX_WAIT_FOR_DRIVER_MIN)

        if req not in got_driver:
            results.append({**base_record, "status": "No Driver Found",
                             "wait_time": None, "trip_duration": None, "distance": None})
            return

        driver_counters[vehicle_type] = driver_counters.get(vehicle_type, 0) + 1
        driver_num = ((driver_counters[vehicle_type] - 1) % pool.capacity) + 1
        vt_code = vehicle_type.replace(" ", "").replace("/", "")[:3].upper()
        driver_id = f"DRV-{vt_code}-{driver_num:02d}"
        base_record["driver_id"] = driver_id

        wait_time = random.choice(stats["vtat_samples"]) if stats["vtat_samples"] else stats["avg_vtat"]
        yield env.timeout(wait_time)

        if random.random() < stats["p_customer_cancel"]:
            results.append({**base_record, "status": "Cancelled by Customer",
                             "wait_time": wait_time, "trip_duration": None, "distance": None})
            return

        if random.random() < stats["p_driver_cancel"]:
            results.append({**base_record, "status": "Cancelled by Driver",
                             "wait_time": wait_time, "trip_duration": None, "distance": None})
            return

        trip_duration = random.choice(stats["ctat_samples"]) if stats["ctat_samples"] else stats["avg_ctat"]
        distance = random.choice(stats["distance_samples"]) if stats["distance_samples"] else stats["avg_distance"]
        yield env.timeout(trip_duration)

        status = "Incomplete" if random.random() < stats["p_incomplete"] else "Completed"
        results.append({**base_record, "status": status,
                         "wait_time": wait_time, "trip_duration": trip_duration,
                         "distance": distance})


def request_arrivals(env, driver_pools, driver_counters, stats, results, demand_multiplier):
    """Generates ride requests at a rate that varies by hour, matching real demand shape."""
    request_id = 0
    daily_target = stats["avg_daily_requests"] * demand_multiplier

    while True:
        current_hour = int((env.now // 60) % 24)
        weight = stats["hourly_weights"].get(current_hour, 1 / 24)
        rate_per_min = max((daily_target * weight) / 60, 1e-6)

        yield env.timeout(random.expovariate(rate_per_min))
        request_id += 1
        env.process(handle_request(env, request_id, driver_pools, driver_counters, stats, results))


def run_simulation(num_drivers=NUM_DRIVERS, demand_multiplier=1.0,
                    sim_duration_min=SIM_DURATION_MIN, seed=RANDOM_SEED,
                    stats=None, enable_shift_dynamics=ENABLE_SHIFT_DYNAMICS,
                    min_active_fraction=MIN_ACTIVE_FRACTION):
    """Runs one simulation and returns (results_df, stats)."""
    random.seed(seed)
    if stats is None:
        stats = load_stats()

    env = simpy.Environment()

    allocation = allocate_driver_pools(num_drivers, stats["vehicle_types"], stats["vehicle_type_weights"])
    driver_pools = {vt: simpy.PriorityResource(env, capacity=count)
                     for vt, count in allocation.items() if count > 0}

    if enable_shift_dynamics:
        for vt, pool in driver_pools.items():
            ShiftController(env, pool, pool.capacity, stats["hourly_weights"], min_active_fraction)

    driver_counters = {}
    results = []

    env.process(request_arrivals(env, driver_pools, driver_counters, stats, results, demand_multiplier))
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

    print(f"\n=== Simulation done: {len(df)} requests over {SIM_DURATION_MIN} minutes, {NUM_DRIVERS} drivers "
          f"(shift dynamics: {ENABLE_SHIFT_DYNAMICS}) ===")
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