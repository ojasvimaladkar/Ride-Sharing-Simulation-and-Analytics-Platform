// ---------- Element references ----------
const numDriversInput = document.getElementById("numDrivers");
const numDriversVal = document.getElementById("numDriversVal");
const demandInput = document.getElementById("demandMultiplier");
const demandVal = document.getElementById("demandVal");
const seedInput = document.getElementById("seed");
const runSimBtn = document.getElementById("runSimBtn");
const runScenariosBtn = document.getElementById("runScenariosBtn");
const downloadBtn = document.getElementById("downloadBtn");
const loadingOverlay = document.getElementById("loadingOverlay");

let outcomeChart, hourlyChart, scenarioChart;
let lastSample = [];

numDriversInput.addEventListener("input", () => {
  numDriversVal.textContent = numDriversInput.value;
});
demandInput.addEventListener("input", () => {
  demandVal.textContent = parseFloat(demandInput.value).toFixed(1) + "x";
});

function showLoading(show) {
  loadingOverlay.style.display = show ? "flex" : "none";
}

async function runSimulation() {
  showLoading(true);
  try {
    const payload = {
      num_drivers: parseInt(numDriversInput.value, 10),
      demand_multiplier: parseFloat(demandInput.value),
      seed: parseInt(seedInput.value, 10),
    };

    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    renderKpis(data.kpis);
    renderOutcomeChart(data.outcome_counts);
    renderHourlyChart(data.hourly);
    renderTable(data.sample);

    lastSample = data.sample;
    downloadBtn.disabled = false;

    document.getElementById("kpiSection").style.display = "grid";
    document.getElementById("chartsSection").style.display = "grid";
    document.getElementById("tableSection").style.display = "block";
  } catch (err) {
    alert("Simulation failed: " + err.message);
    console.error(err);
  } finally {
    showLoading(false);
  }
}

function renderKpis(kpis) {
  document.getElementById("kpiCompletion").textContent =
    (kpis.completion_rate_pct ?? 0) + "%";
  document.getElementById("kpiNoDriver").textContent =
    (kpis.no_driver_found_rate_pct ?? 0) + "%";
  document.getElementById("kpiUtilization").textContent =
    (kpis.driver_utilization_pct ?? 0) + "%";
  document.getElementById("kpiWait").textContent =
    (kpis.avg_wait_time_min ?? 0) + " min";
}

function renderOutcomeChart(outcomeCounts) {
  const ctx = document.getElementById("outcomeChart");
  const labels = Object.keys(outcomeCounts);
  const values = Object.values(outcomeCounts);

  if (outcomeChart) outcomeChart.destroy();
  outcomeChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Rides", data: values, backgroundColor: "#4C72B0" }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
        y: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
      },
    },
  });
}

function renderHourlyChart(hourly) {
  const ctx = document.getElementById("hourlyChart");
  const labels = Object.keys(hourly).sort((a, b) => a - b);
  const values = labels.map((h) => hourly[h]);

  if (hourlyChart) hourlyChart.destroy();
  hourlyChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.map((h) => h + ":00"),
      datasets: [{
        label: "Requests",
        data: values,
        borderColor: "#DD8452",
        backgroundColor: "rgba(221,132,82,0.2)",
        tension: 0.3,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
        y: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
      },
    },
  });
}

function renderTable(sample) {
  if (!sample || sample.length === 0) return;
  const head = document.getElementById("ridesTableHead");
  const body = document.getElementById("ridesTableBody");

  const columns = Object.keys(sample[0]);
  head.innerHTML = columns.map((c) => `<th>${c}</th>`).join("");
  body.innerHTML = sample.map((row) =>
    "<tr>" + columns.map((c) => `<td>${row[c] ?? ""}</td>`).join("") + "</tr>"
  ).join("");
}

async function runScenarios() {
  showLoading(true);
  try {
    const res = await fetch("/api/scenarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed: parseInt(seedInput.value, 10) }),
    });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const results = await res.json();

    const tbody = document.getElementById("scenarioTableBody");
    tbody.innerHTML = results.map((r) => `
      <tr>
        <td>${r.scenario}</td>
        <td>${r.completion_rate_pct ?? "-"}</td>
        <td>${r.no_driver_found_rate_pct ?? "-"}</td>
        <td>${r.driver_utilization_pct ?? "-"}</td>
        <td>${r.avg_wait_time_min ?? "-"}</td>
      </tr>
    `).join("");

    const ctx = document.getElementById("scenarioChart");
    if (scenarioChart) scenarioChart.destroy();
    scenarioChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: results.map((r) => r.scenario),
        datasets: [{
          label: "Completion Rate (%)",
          data: results.map((r) => r.completion_rate_pct),
          backgroundColor: "#55A868",
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
          y: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
        },
      },
    });

    document.getElementById("scenarioSection").style.display = "block";
  } catch (err) {
    alert("Scenario run failed: " + err.message);
    console.error(err);
  } finally {
    showLoading(false);
  }
}

function downloadCsv() {
  if (!lastSample.length) return;
  const columns = Object.keys(lastSample[0]);
  const rows = [columns.join(",")].concat(
    lastSample.map((row) => columns.map((c) => row[c]).join(","))
  );
  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "synthetic_rides_sample.csv";
  a.click();
  URL.revokeObjectURL(url);
}

runSimBtn.addEventListener("click", runSimulation);
runScenariosBtn.addEventListener("click", runScenarios);
downloadBtn.addEventListener("click", downloadCsv);

runSimulation();