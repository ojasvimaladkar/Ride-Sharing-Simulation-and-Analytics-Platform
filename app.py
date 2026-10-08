"""
Flask backend for the Ride-Sharing Simulation dashboard.
Serves the frontend and exposes simulation/scenario endpoints as JSON APIs.
Run: python app.py   then open http://localhost:5000
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import numpy as np
from flask import Flask, jsonify, request, render_template, send_file

from src.simulation.simulate import run_simulation, load_stats, SIM_DURATION_MIN
from src.analytics.metrics import compute_kpis

app = Flask(__name__, template_folder="templates", static_folder="static")

_stats_cache = None
REPORTS_DIR = Path(__file__).resolve().parent / "outputs" / "reports"
FULL_LOG_PATH = REPORTS_DIR / "dashboard_full_log.csv"


def get_stats():
    global _stats_cache
    if _stats_cache is None:
        _stats_cache = load_stats()
    return _stats_cache


def hourly_counts_by_status(df, status=None):
    """Returns a 24-length dict of counts by hour, optionally filtered to one status."""
    if len(df) == 0 or "hour" not in df.columns:
        return {str(h): 0 for h in range(24)}
    subset = df if status is None else df[df["status"] == status]
    counts = subset.groupby("hour").size().reindex(range(24), fill_value=0)
    return {str(k): int(v) for k, v in counts.items()}


def demand_completion_correlation(hourly_requests: dict, hourly_completed: dict):
    """Pearson correlation between requests-per-hour and completions-per-hour."""
    req = np.array([hourly_requests[str(h)] for h in range(24)], dtype=float)
    comp = np.array([hourly_completed[str(h)] for h in range(24)], dtype=float)
    if req.std() == 0 or comp.std() == 0:
        return None  # undefined (e.g. zero demand, or no variation across hours)
    r = np.corrcoef(req, comp)[0, 1]
    return round(float(r), 3)


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

    outcome_counts = df["status"].value_counts().to_dict() if len(df) else {}

    hourly_requests = hourly_counts_by_status(df)
    hourly_completed = hourly_counts_by_status(df, status="Completed")
    correlation = demand_completion_correlation(hourly_requests, hourly_completed)

    # Save the FULL transaction log (every request: demand + driver assigned),
    # not just the preview sample -- overwrites each run so it always reflects
    # the most recent simulation.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(FULL_LOG_PATH, index=False)

    sample_df = df.head(50)
    sample = sample_df.astype(object).where(sample_df.notna(), None).to_dict(orient="records") if len(df) else []

    return jsonify({
        "kpis": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in kpis.items()},
        "outcome_counts": outcome_counts,
        "hourly": hourly_requests,
        "hourly_completed": hourly_completed,
        "demand_completion_correlation": correlation,
        "sample": sample,
        "total_requests": len(df),
    })


@app.route("/api/download-full")
def api_download_full():
    if not FULL_LOG_PATH.exists():
        return jsonify({"error": "No simulation has been run yet"}), 404
    return send_file(FULL_LOG_PATH, as_attachment=True, download_name="ride_simulation_full_log.csv")


@app.route("/api/scenarios", methods=["POST"])
def api_scenarios():
    data = request.get_json(force=True) or {}
    seed = int(data.get("seed", 42))

    scenario_defs = [
        ("Baseline", 25, 1.0),
        ("Low Supply (12 drivers)", 12, 1.0),
        ("High Supply (45 drivers)", 45, 1.0),
        ("High Demand (+30%)", 25, 1.3),
        ("Low Demand (-30%)", 25, 0.7),
        ("Zero Demand", 25, 0.0),
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