# Member Role Division & Viva Speaking Scripts

> **Project:** Ride-Sharing Simulation and Analytics Platform (ROSP Major Project)  
> **Purpose:** Detailed script, code ownership, technical architecture, and exact viva lines for each of the 3 team members in front of the external examiner.

---

## Quick Summary of the 3 Roles

| Member | Module & Role | Core Files |
| :--- | :--- | :--- |
| **Member 1** | Data Engineering, EDA & Statistical Validation |  `src/preprocessing/preprocess.py`<br>`src/eda/eda.py`<br>`src/analytics/metrics.py` (KS test part) |
| **Member 2** | Core Discrete-Event Simulation Engine  | `src/simulation/simulate.py`<br>`tune_drivers_v2.py` |
| **Member 3** | What-If Scenarios, Analytics & Web Dashboard | `src/scenarios/what_if.py`<br>`app.py`<br>`templates/index.html`<br>`static/script.js` |

---

# Member 1: Data Engineering, EDA & Statistical Validation

### 1. Code & Module Ownership
- **`src/preprocessing/preprocess.py`**: Reads raw Kaggle CSV, drops duplicates, parses dates into `datetime`, `hour`, `date_only`, cleans categorical columns, casts numerical metrics.
- **`src/eda/eda.py`**: Computes booking status frequencies, hourly demand profiles, vehicle type distributions, and plots EDA charts to `outputs/figures/`.
- **`src/analytics/metrics.py` (Validation Section)**: Runs two-sample Kolmogorov-Smirnov (`ks_2samp`) tests comparing simulated vs. real distributions.

---

### 2. Technical Architecture & Working (What Member 1 Must Understand)
1. **The Dataset:** 150,000 real ride bookings from Delhi-NCR (2024), licensed under CC BY-SA 4.0.
2. **Key Findings from EDA:**
   - 62% of rides complete successfully.
   - 18% cancelled by driver, 7% cancelled by customer, 7% unserved (no driver found), 6% incomplete.
   - Peak hour is **6:00 PM** with 12,397 bookings (evening rush hour).
   - Demand across days of the week is roughly flat.
   - 7 vehicle types: Auto (25%), Go Mini (20%), Go Sedan (18%), Bike (15%), Premier Sedan (12%), eBike (7%), Uber XL (3%).
3. **Statistical Validation (Kolmogorov-Smirnov Test):**
   - We do not just "eyeball" charts; we use a formal mathematical test (`scipy.stats.ks_2samp`).
   - The test measures $D$, the maximum vertical distance between the empirical cumulative distribution functions of simulated data and real data.
   - **Result:** Wait time $D = 0.091$, Trip duration $D = 0.027$, Distance $D = 0.046$. All $D < 0.1$, proving a **strong statistical match**.

---

### 3. Exact Speaking Script in Front of External Examiner

> **Opening Statement:**  
> *"Good morning, Sir/Ma'am. My contribution covers the Data Engineering, Exploratory Data Analysis, and Statistical Validation pipeline.*  
> *Rather than generating arbitrary synthetic numbers, our simulation is calibrated strictly against a real-world dataset of 150,000 Uber bookings from the Delhi-NCR region.*  
>  
> *In `preprocess.py`, I cleaned the raw dataset: handled missing values, standardized timestamps into 24-hour intervals, and extracted the operational features like vehicle categories, pickup/drop clusters, wait times (VTAT), trip durations (CTAT), and fares.*  
>  
> *In `eda.py`, I analyzed the fundamental dynamics of the NCR market: we identified that peak demand occurs at 6 PM with nearly 12,400 rides, that Auto and Go Mini represent 45% of total demand, and that the baseline completion rate is 62%.*  
>  
> *Finally, in `metrics.py`, I implemented the Kolmogorov-Smirnov goodness-of-fit validation. Instead of simply looking at histograms, we scientifically test whether our simulated trip duration, wait time, and distance distributions match the real data. For all three metrics, our Kolmogorov-Smirnov D-statistic is under 0.1, which formally proves our simulation reproduces true real-world distributions with high statistical fidelity."*

---

### 4. Likely Viva Questions for Member 1 & Model Answers

* **Q: Why did you clean the dataset, and what did you drop?**  
  *Answer:* *"We dropped duplicate rows and rows with corrupted date formats. We preserved legitimate missing values in cancellation reasons and ratings because a completed trip naturally has no cancellation reason."*
* **Q: What is the peak demand hour and why does it matter?**  
  *Answer:* *"Peak demand is 6:00 PM (evening rush hour). It matters because our simulation uses these hourly weights to drive a non-homogeneous arrival process, so rush hours see higher ride requests than overnight hours."*
* **Q: What does the Kolmogorov-Smirnov (KS) test tell you?**  
  *Answer:* *"It tests whether two continuous distributions differ significantly. The D-statistic is the maximum gap between the two cumulative distribution functions. A value of D < 0.1 indicates that our simulated distributions closely match the real dataset."*

---

# Member 2: Core Discrete-Event Simulation Engine

### 1. Code & Module Ownership
- **`src/simulation/simulate.py`**: The complete discrete-event simulation engine written with SimPy. Contains `ShiftController`, `PhantomDriver`, `handle_request()`, `request_arrivals()`, and driver pool allocation.
- **`tune_drivers_v2.py`**: Fleet calibration script that ran multi-seed optimization to determine the optimal fleet size (25 drivers).

---

### 2. Technical Architecture & Working (What Member 2 Must Understand)
1. **Why Discrete-Event Simulation (SimPy)?**
   - Unlike time-step simulation (which loops minute-by-minute and wastes CPU during quiet periods), SimPy is **event-driven**.
   - It maintains an internal priority queue of scheduled events and jumps the clock directly to the next event time (e.g., from $t = 12.4$ to $t = 18.9$).
2. **Vehicle Pool Sizing (Largest Remainder Method):**
   - The total fleet (25 drivers) is partitioned across 7 vehicle types based on empirical market fractions using largest-remainder integer rounding.
3. **Shift Dynamics & Phantom Drivers:**
   - Driver supply varies over 24 hours (fewer at 4 AM, more at 6 PM).
   - Rather than abruptly deleting driver instances (which would crash active rides), we spawn non-preemptive `PhantomDriver` objects at high priority during quiet hours. They claim free slots as drivers finish trips and hold them until demand rises again.
4. **Behavioral Customer Cancellations:**
   - Riders waiting longer have higher cancellation rates: $P(\text{cancel}) = P_{\text{base}} \times (0.5 + 0.08 \times \text{wait\_time})$. Fast pickups have ~3.5% cancellation, while 15-minute waits reach ~17%.
5. **Joint Sampling:**
   - Trip duration, distance, and fare are sampled as a coupled tuple `(Avg CTAT, Ride Distance, Booking Value)` directly from real trips, preserving physical speed and pricing relationships.

---

### 3. Exact Speaking Script in Front of External Examiner

> **Opening Statement:**  
> *"Good morning, Sir/Ma'am. My contribution is the core Simulation Engine and queueing architecture built with SimPy in `simulate.py`.*  
>  
> *We chose Discrete-Event Simulation over naive time-step loops. Instead of executing thousands of empty minute-by-minute iterations, SimPy advances time asynchronously from event to event—request arrival, vehicle assignment, pickup dispatch, and drop-off.*  
>  
> *I implemented four major architectural features:*  
> *First, vehicle-type segregated driver pools: riders requesting an Auto are matched strictly to Auto drivers, partitioned proportionally using the Largest Remainder algorithm.*  
>  
> *Second, 24-hour shift dynamics using 'Phantom Drivers': during quiet overnight hours, background phantom processes occupy idle fleet slots as trips complete, scaling active supply down without interrupting any passenger mid-ride.*  
>  
> *Third, dynamic behavioral cancellations: customer cancellations are coupled to wait time, so riders waiting near the 15-minute queue timeout cancel at much higher rates than riders picked up immediately.*  
>  
> *Fourth, joint trip sampling: we sample duration, distance, and booking fare together as a coupled tuple from real completed rides, ensuring realistic speed and pricing correlations.*  
>  
> *In `tune_drivers_v2.py`, I calibrated the system across multiple random seeds, finding that a fleet of 25 drivers precisely reproduces the dataset's target 7% unserved rate."*

---

### 4. Likely Viva Questions for Member 2 & Model Answers

* **Q: Why SimPy instead of a normal loop (`for minute in range(1440)`)?**  
  *Answer:* *"SimPy is an event-driven framework. It avoids iterating through idle clock cycles, handles simultaneous asynchronous requests, and provides built-in `PriorityResource` pools for queue management."*
* **Q: How do you handle driver shifts without kicking passengers out of cars?**  
  *Answer:* *"Through our `PhantomDriver` design pattern. When supply needs to decrease, a phantom driver requests a slot in the vehicle pool. It waits until an active driver finishes their trip, then holds the slot off-duty, achieving smooth non-preemptive shift transitions."*
* **Q: What is joint sampling and why did you use it?**  
  *Answer:* *"If we sampled distance and duration independently, a ride might randomly get a 2 km distance and a 45-minute travel time. Joint sampling draws `(distance, duration, fare)` together from real historical records, preserving realistic traffic speeds and fares."*

---

# Member 3: What-If Scenarios, Analytics & Interactive Web Dashboard

### 1. Code & Module Ownership
- **`src/scenarios/what_if.py`**: Executes the 6 operational scenarios and outputs comparative tables and figures.
- **`app.py`**: Flask REST API backend exposing `/api/simulate`, `/api/scenarios`, and `/api/download-full`.
- **`templates/index.html` & `static/script.js` & `static/style.css`**: The interactive web dashboard with Chart.js visualizations.
- **`src/analytics/metrics.py` (KPI Section)**: Computes completion rates, unserved rates, driver utilization %, and platform revenue.

---

### 2. Technical Architecture & Working (What Member 3 Must Understand)
1. **The 6 What-If Scenarios:**
   - **Baseline:** 25 drivers, 1.0× demand (Matches real data benchmarks: 68% complete, ~32% utilization, ~₹1.26L revenue).
   - **Low Supply (18 drivers):** Unserved rides jump to 13%, utilization jumps to 40%, wait times rise.
   - **High Supply (35 drivers):** Unserved rides drop to 1.2%, but fleet utilization falls to 23.6% (driver idle holding cost).
   - **High Demand (+30%):** Revenue rises to ₹1.58L, utilization reaches 41%.
   - **Low Demand (-30%):** Revenue drops to ₹86K, utilization falls to 22.8%.
   - **Zero Demand (0.0×):** Null control baseline: 0 requests, 0 completions, 0% utilization, ₹0 revenue, exactly 1,440 minutes of idle time.
2. **Key Metrics Formulated:**
   - **Driver Utilization:** Actively engaged minutes ($\text{dispatch} + \text{trip}$) divided by total available fleet minutes ($N \times 1440$).
   - **Platform Revenue:** Total fares collected from completed trips.
   - **The Denominator Effect:** Completion % stays around 60–70% across runs because cancellations are per-request probabilities; what actually scales with demand is **absolute completed rides** and **revenue**.
3. **Dashboard & API Pipeline:**
   - Flask server serves the frontend and handles async POST requests from `script.js`.
   - `/api/download-full` streams the complete 24-hour transaction log (`dashboard_full_log.csv`) directly to the browser.

---

### 3. Exact Speaking Script in Front of External Examiner

> **Opening Statement:**  
> *"Good morning, Sir/Ma'am. My contribution focuses on Scenario Analysis, Operational KPIs, and the Interactive Full-Stack Dashboard.*  
>  
> *The ultimate purpose of this simulation is to give decision-makers a risk-free environment to answer 'what-if' business questions.*  
>  
> *In `what_if.py`, I formulated 6 distinct operational scenarios. For example, in our Low Supply scenario, reducing drivers to 18 causes unserved requests to double from 5% to 13%, while increasing drivers to 35 reduces unserved rides to 1.2% but lowers driver utilization to 23%, creating significant idle holding costs.*  
>  
> *I also implemented the Zero-Demand scenario. In systems engineering, testing at lambda = 0 is the null control condition. It proves that our simulation handles boundary conditions gracefully without divide-by-zero crashes, and establishes our baseline fleet holding cost—at zero demand, drivers log exactly 1,440 minutes of idle time.*  
>  
> *In `app.py` and the frontend, I developed the full-stack web dashboard using Flask, Vanilla CSS, and Chart.js. Users can interactively adjust fleet size and demand, inspect live KPI cards—including completion rates, driver utilization, and platform revenue—view hourly demand curves, compare all 6 scenarios side-by-side, and export complete transaction CSV logs for auditability."*

---

### 4. Likely Viva Questions for Member 3 & Model Answers

* **Q: Why does completion rate stay around 60%–70% even when you change demand?**  
  *Answer:* *"That is known as the Denominator Effect. Because customer and driver cancellation probabilities are per-booking rates, the completion percentage remains bounded. What actually scales with demand is the absolute number of completed trips and total platform revenue."*
* **Q: What is the purpose of the 0-demand scenario requested by the professor?**  
  *Answer:* *"It serves as the null control condition. It proves mathematical robustness by verifying that zero-division errors do not crash rate calculations, and it establishes the operational baseline where driver utilization is 0% and idle time is exactly 1,440 minutes."*
* **Q: How does the web dashboard communicate with the simulation engine?**  
  *Answer:* *"The frontend uses asynchronous `fetch()` calls to send user parameters to Flask REST endpoints (`/api/simulate` and `/api/scenarios`). The server runs the SimPy engine in memory and returns JSON containing KPIs, hourly counts, and sample logs, which Chart.js renders dynamically on canvas elements."*

---

## Final Team Presentation Flow (When Presenting Together)

1. **Member 1 speaks first (1–2 mins):** Introduces the NCR dataset, data cleaning in Pandas, real-world EDA findings, and the Kolmogorov-Smirnov statistical validation.
2. **Member 2 speaks second (2 mins):** Explains why SimPy discrete-event simulation was chosen, vehicle-type pool splitting, phantom driver shift mechanics, dynamic cancellations, and joint sampling.
3. **Member 3 speaks third (2 mins):** Runs the live web dashboard in the browser, demonstrates the sliders, explains the 6 what-if scenarios, highlights the zero-demand baseline and platform revenue, and concludes.
