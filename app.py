"""
Flask backend for the Ride-Sharing Simulation dashboard.
Serves the frontend and exposes simulation/scenario endpoints as JSON APIs.
Run: python app.py   then open http://localhost:5000
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from flask import Flask, jsonify, request, render_template

from src.simulation.simulate import run_simulation, load_stats, SIM_DURATION_MIN
from src.analytics.metrics import compute_kpis

app = Flask(__name__, template_folder="templates", static_folder="static")

_stats_cache = None


def get_stats():
    global _stats_cache
    if _stats_cache is None:
        _stats_cache = load_stats()
    return _stats_cache


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    stats = get_stats()
    clean = {k: v for k, v in stats.items() if isinstance(v, (int, float))}
    return jsonify(clean)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    data = request.get_json(force=True) or {}
    num_drivers = int(data.get("num_drivers", 9))
    demand_multiplier = float(data.get("demand_multiplier", 1.0))
    seed = int(data.get("seed", 42))

    stats = get_stats()
    df, _ = run_simulation(num_drivers=num_drivers, demand_multiplier=demand_multiplier,
                            seed=seed, stats=stats)
    kpis = compute_kpis(df, num_drivers, SIM_DURATION_MIN)

    outcome_counts = df["status"].value_counts().to_dict()

    hourly = {}
    if "hour" in df.columns:
        hourly = {str(k): int(v) for k, v in
                  df.groupby("hour").size().reindex(range(24), fill_value=0).items()}

    sample_df = df.head(50)
    sample = sample_df.astype(object).where(sample_df.notna(), None).to_dict(orient="records")

    return jsonify({
        "kpis": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in kpis.items()},
        "outcome_counts": outcome_counts,
        "hourly": hourly,
        "sample": sample,
        "total_requests": len(df),
    })


@app.route("/api/scenarios", methods=["POST"])
def api_scenarios():
    data = request.get_json(force=True) or {}
    seed = int(data.get("seed", 42))

    scenario_defs = [
        ("Baseline", 20, 1.0),
        ("Low Supply (15 drivers)", 15, 1.0),
        ("High Supply (30 drivers)", 30, 1.0),
        ("High Demand (+30%)", 20, 1.3),
        ("Low Demand (-30%)", 20, 0.7),
    ]

    stats = get_stats()
    results = []
    for label, n, mult in scenario_defs:
        df, _ = run_simulation(num_drivers=n, demand_multiplier=mult, seed=seed, stats=stats)
        kpis = compute_kpis(df, n, SIM_DURATION_MIN)
        kpis = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in kpis.items()}
        kpis["scenario"] = label
        results.append(kpis)

    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=False, port=5000)