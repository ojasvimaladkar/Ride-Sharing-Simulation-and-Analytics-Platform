"""
Tuning script v2: averages 5 random seeds per driver count to find a
statistically stable NUM_DRIVERS value, rather than trusting one noisy run.
Run from your project root: python tune_drivers_v2.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import statistics
from src.simulation.simulate import run_simulation, load_stats

TARGET_NO_DRIVER_PCT = 7.0
SEEDS = [1, 2, 3, 4, 5]
DRIVER_COUNTS = [20, 22, 25, 28, 30, 35, 40]

print("Loading dataset stats once...")
stats = load_stats()

print(f"\n{'Drivers':>8} | {'Avg No-Driver %':>16} | {'Std Dev':>8} | {'Avg Completed %':>16} | Gap from target")
print("-" * 80)

results = []
for num_drivers in DRIVER_COUNTS:
    no_driver_rates = []
    completed_rates = []

    for seed in SEEDS:
        df, _ = run_simulation(num_drivers=num_drivers, seed=seed, stats=stats, enable_shift_dynamics=True)        
        total = len(df)
        counts = df["status"].value_counts()
        no_driver_rates.append(counts.get("No Driver Found", 0) / total * 100)
        completed_rates.append(counts.get("Completed", 0) / total * 100)

    avg_no_driver = statistics.mean(no_driver_rates)
    std_no_driver = statistics.stdev(no_driver_rates)
    avg_completed = statistics.mean(completed_rates)
    gap = abs(avg_no_driver - TARGET_NO_DRIVER_PCT)

    results.append((num_drivers, avg_no_driver, gap))
    print(f"{num_drivers:>8} | {avg_no_driver:>15.1f}% | {std_no_driver:>7.2f} | {avg_completed:>15.1f}% | {gap:.2f}")

best = min(results, key=lambda x: x[2])
print(f"\nBest match (averaged over {len(SEEDS)} seeds): NUM_DRIVERS = {best[0]}")
print(f"(Avg No Driver Found = {best[1]:.1f}%, target = {TARGET_NO_DRIVER_PCT}%)")
print(f"\nUpdate NUM_DRIVERS = {best[0]} in src/simulation/simulate.py")
print("\nNote the Std Dev column -- a low value means that driver count gives")
print("consistent results across different random seeds (more trustworthy);")
print("a high value means the result you get depends heavily on luck.")