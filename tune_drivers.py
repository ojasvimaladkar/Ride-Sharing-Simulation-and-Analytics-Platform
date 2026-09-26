"""
Tuning script: finds the NUM_DRIVERS value that gets closest to the real
No Driver Found rate (7.0%) under the new vehicle-type-segmented fleet.
Run from your project root: python tune_drivers.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.simulation.simulate import run_simulation, load_stats

TARGET_NO_DRIVER_PCT = 7.0  # from your real dataset

print("Loading dataset stats once...")
stats = load_stats()

print("\nVehicle type distribution in your real dataset:")
for vt, w in zip(stats["vehicle_types"], stats["vehicle_type_weights"]):
    print(f"  {vt}: {w*100:.1f}%")

print(f"\n{'Drivers':>8} | {'Total Req':>9} | {'Completed %':>11} | {'No Driver %':>11} | {'Utilization %':>13} | Gap from target")
print("-" * 80)

results = []
for num_drivers in [9, 12, 15, 18, 20, 25, 30, 35, 40, 50, 60]:
    df, _ = run_simulation(num_drivers=num_drivers, stats=stats)
    total = len(df)
    counts = df["status"].value_counts()

    no_driver_pct = counts.get("No Driver Found", 0) / total * 100
    completed_pct = counts.get("Completed", 0) / total * 100

    occupied = df["wait_time"].fillna(0) + df["trip_duration"].fillna(0)
    utilization = occupied.sum() / (num_drivers * 1440) * 100

    gap = abs(no_driver_pct - TARGET_NO_DRIVER_PCT)
    results.append((num_drivers, no_driver_pct, gap))

    print(f"{num_drivers:>8} | {total:>9} | {completed_pct:>10.1f}% | {no_driver_pct:>10.1f}% | {utilization:>12.1f}% | {gap:.2f}")

best = min(results, key=lambda x: x[2])
print(f"\nBest match: NUM_DRIVERS = {best[0]} (No Driver Found = {best[1]:.1f}%, target = {TARGET_NO_DRIVER_PCT}%)")
print(f"\nUpdate NUM_DRIVERS = {best[0]} in src/simulation/simulate.py")