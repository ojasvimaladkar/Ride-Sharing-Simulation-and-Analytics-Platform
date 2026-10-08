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

const INK = "#dde1e6";
const GRID = "#262b33";
const AMBER = "#f2a93b";
const TEAL = "#3fc1b0";

let outcomeChart, hourlyChart, scenarioChart;
let lastSample = [];

numDriversInput.addEventListener("input", () => {
  numDriversVal.textContent = numDriversInput.value;
});
demandInput.addEventListener("input", () => {
  demandVal.textContent = parseFloat(demandInput.value).toFixed(1) + "×";
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
    renderCorrelationChart(data.hourly, data.hourly_completed, data.demand_completion_correlation);
    document.getElementById("correlationSection").style.display = "block";
    renderTable(data.sample);

    lastSample = data.sample;
    downloadBtn.disabled = false;

    document.getElementById("tickerSection").style.display = "flex";
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
      datasets: [{ label: "Rides", data: values, backgroundColor: AMBER, borderRadius: 2 }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: GRID } },
        y: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: GRID } },
      },
    },
  });
}

let correlationChart;

function renderCorrelationChart(hourlyRequests, hourlyCompleted, correlation) {
  const ctx = document.getElementById("correlationChart");
  const labels = Object.keys(hourlyRequests).sort((a, b) => a - b);

  const corrText = document.getElementById("correlationValue");
  corrText.textContent = correlation === null
    ? "(undefined \u2014 no variation to correlate)"
    : `r = ${correlation} (Pearson correlation)`;

  if (correlationChart) correlationChart.destroy();
  correlationChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.map((h) => h + ":00"),
      datasets: [
        {
          label: "Requests",
          data: labels.map((h) => hourlyRequests[h]),
          borderColor: AMBER,
          backgroundColor: "rgba(242,169,59,0.08)",
          tension: 0.3,
          pointRadius: 0,
        },
        {
          label: "Completed",
          data: labels.map((h) => hourlyCompleted[h]),
          borderColor: TEAL,
          backgroundColor: "rgba(63,193,176,0.08)",
          tension: 0.3,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: true, labels: { color: INK, font: { family: "IBM Plex Mono", size: 11 } } },
      },
      scales: {
        x: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 10 } }, grid: { color: GRID } },
        y: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: GRID } },
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
        borderColor: TEAL,
        backgroundColor: "rgba(63,193,176,0.12)",
        tension: 0.3,
        fill: true,
        pointRadius: 0,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 10 } }, grid: { color: GRID } },
        y: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: GRID } },
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

// ---------- Scenario comparison ----------
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
        <td>${r.completion_rate_pct ?? "-"}%</td>
        <td>${r.no_driver_found_rate_pct ?? "-"}%</td>
        <td>${r.driver_utilization_pct ?? "-"}%</td>
        <td>${r.avg_wait_time_min ?? "-"} min</td>
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
          backgroundColor: TEAL,
          borderRadius: 2,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 10 } }, grid: { color: GRID } },
          y: { ticks: { color: INK, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: GRID } },
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

// ---------- CSV download ----------
function downloadCsv() {
  window.location.href = "/api/download-full";
}

runSimBtn.addEventListener("click", runSimulation);
runScenariosBtn.addEventListener("click", runScenarios);
downloadBtn.addEventListener("click", downloadCsv);

runSimulation();