# PTIXIAKI — Complete Project Context & Handoff

**Project:** Bachelor's thesis (Πτυχιακή Εργασία), Department of Informatics, Ionian University (Ιόνιο Πανεπιστήμιο)  
**Student:** Γεώργιος Ιωάννου (George Ioannou), student ID **INF2021006**  
**Supervisor:** Ελένη Χριστοπούλου  
**Context snapshot:** **27 October 2026**  
**Purpose:** Upload this file to a new ChatGPT Project / ChatGPT Work task, or add it to a code repository for Codex, so the assistant can continue the thesis without reconstructing the previous discussion.  
**Source:** Consolidated from the student's ChatGPT conversation, supervisor emails copied into that conversation, and shopping research discussed there. It is **not** the official university assignment form, a verified set of email headers, or a record of purchases.

> **IMPORTANT CONTINUITY INSTRUCTION**  
> Treat the decisions marked **CONFIRMED** below as the current scope. Treat proposed technologies and items marked **PLANNED** as preferences rather than things already installed or purchased. Do not silently expand this into a multi-node system, add a second temperature sensor, assume access permissions are already signed, or claim the machine-learning model will outperform simpler baselines. Start with the smallest testable end-to-end implementation.

---

## 1. One-minute summary

Build a small but complete **IoT environmental monitoring and anomaly-detection system for one real AV/equipment space or rack**. It will use **exactly one ESP32 development board and one physical environmental sensor module**, with a **no-soldering** build. The latest hardware choice is a **Seeed Grove BME280**, which measures temperature, relative humidity, and barometric pressure in one module. The ESP32 sends readings over **Wi-Fi/MQTT** to a backend; readings are stored as time series and displayed in a browser. Collect **3–6 weeks** of real-world data; compare fixed thresholds, temperature change rate, statistical detectors, and at least one ML anomaly detector, using documented controlled/synthetic anomalies and rigorous evaluation metrics.

**Initial handoff status on 27 October 2026:** Thesis application **submitted successfully** (student confirmed on 19 October); supervisor expressed agreement with the research direction and proposed title/committee. At that point, no hardware purchase, code implementation, deployment, or data collection was confirmed.

### Implementation update — 27 October 2026

The first **software-only MVP** is now implemented and verified with explicitly synthetic data:

- A seeded synthetic publisher sends the one configured device's temperature, relative humidity and pressure over MQTT QoS 1.
- A separate Python ingestion worker validates units, physical plausibility, UTC timestamps and the configured device ID, and writes to InfluxDB 2. It retries failed writes and acknowledges valid messages only after storage succeeds.
- FastAPI exposes authenticated database readiness, latest readings, and bounded chronological history. Synthetic and sensor records are stored and queried separately; identical message redelivery is idempotent.
- A React dashboard shows current readings, a timestamp-based history chart, source/window/metric controls, and explicit loading, empty, stale and error states. It uses UTC and labels simulation visibly.
- Docker Compose runs the broker, database, worker, API and web UI, with an optional simulator profile. Dependency lockfiles, local credential initialization and setup instructions are in the repository.
- Validation completed: **74 backend tests**, **7 frontend tests**, the frontend production build, container startup, actual MQTT→InfluxDB→HTTP checks, and desktop/mobile browser checks. The pipeline check verifies duplicate handling, malformed/invalid input rejection and source separation. These are software checks, not research measurements.

**Still unconfirmed or unimplemented:** hardware purchase and firmware, actual BME280 readings, site permission and deployment, 3–6 weeks of real observations, alerts/incident handling, anomaly detectors and their experimental evaluation. No ML performance or real-world monitoring result is claimed. The simulator's five-second interval and the 120-second offline threshold are development defaults, not finalized research settings.

See `README.md` for commands and `docs/telemetry.md` for the implemented contract and delivery limitations. Local `.env` and `data/` contain development credentials/state and must stay out of Git.

---

## 2. Academic context and topic

### Proposed/selected Greek title

**«Σχεδίαση και υλοποίηση συστήματος IoT για την περιβαλλοντική παρακολούθηση χώρου εξοπλισμού με ανίχνευση ανωμαλιών: σύγκριση μεθόδων κατωφλίου και μηχανικής μάθησης»**

### English title

**Design and Implementation of an IoT Environmental Monitoring System for Equipment Spaces with Anomaly Detection: A Comparison of Threshold-Based and Machine Learning Methods**

The supervisor provided this as her *second suggested title*; the student agreed to it. The application was later reported successful. **Verify the exact title as recorded by the university** before using it on the final thesis cover page.

### People

- **Supervisor:** Ελένη Χριστοπούλου — agreed in principle and later expressly confirmed oversight.
- **Proposed other committee members:** κ. Στεφανιδάκης and κ. Ρίγγας; the student accepted this suggestion. **Formal appointment of the three-person committee was not independently verified in the chat.**
- Student is based in **Cyprus**, away from Corfu.

### Motivation

The idea grew from the student's practical experience with professional audiovisual equipment, racks, video processors, networking and IT support. It is intended as a **general academic prototype**. **Do not imply any employer has commissioned, endorsed, or granted permission for it.** The exact installation site has not been specified in the chat.

---

## 3. Confirmed scope vs. choices still open

### CONFIRMED / STRONGLY ESTABLISHED

1. **ONE ESP32 device** only (not two or three separate monitoring nodes).
2. **ONE physical environmental sensor module** only; user specifically does **not** want a second temperature sensor.
3. **NO SOLDERING**. Prefer pre-soldered headers, preterminated cables, and plug-in connections.
4. Monitor **one small, relatively unified real equipment space / one AV rack area**, not a building-wide network of rooms.
5. User **has access** to a real professional equipment space and says they **can obtain** authorization. **Written authorization has not yet been confirmed.**
6. Aim for **3–6 weeks of continuous real data** to capture day/night and weekday/weekend patterns.
7. Dashboard + backend + stored history + alerts + **comparison of anomaly-detection methods**; not just a basic thermometer dashboard.
8. Supervisor wants a **measurable experimental evaluation**, ideally using logged safe controlled anomalies and possibly synthetic anomalies.
9. Keep expenses reasonable; avoid hardware bought just to make the project seem larger.

### PLANNED / SUBJECT TO IMPLEMENTATION

- **Latest preferred sensor:** one **Seeed Grove BME280** breakout (temperature, humidity, pressure). Earlier emails mentioned SHT31/SHT4x, but the latest shopping decision moved to BME280. Confirm the exact product SKU and interface before ordering.
- **Network:** Wi-Fi 2.4 GHz + MQTT; **Eclipse Mosquitto** broker.
- **Backend:** Python + **FastAPI**.
- **Time-series DB:** **InfluxDB**.
- **Web UI:** **React** (preferred as an opportunity to learn frontend development). **Grafana** is the simpler fallback if time is constrained.
- **Local reproducibility:** **Docker Compose**.
- **Analytics:** fixed thresholds, ΔT/Δt, rolling z-score, EWMA, Isolation Forest; **LOF optional**.
- **Notifications:** dashboard alerts and potentially email; exact delivery mechanism not decided.
- **Host:** an always-on computer / mini-server / Raspberry Pi may run broker, API and database. No permanent host has been chosen or verified. A Raspberry Pi 5 has been mentioned in prior discussion as potentially available, but availability/setup should be confirmed before planning around it.

### Explicitly out of scope unless student and supervisor agree to change it

- More ESP32s / multiple sensor nodes / whole-building monitoring.
- Second temperature sensor; separate door, power-meter, or current-sensing modules.
- Soldering, custom PCB design, mains-electrical modifications, or disabling rack fans for experiments.
- Dedicated mobile app, deep-learning requirements, CCTV, or control of rack cooling equipment.

---

## 4. What the supervisor specifically required (19 October 2026 email)

The supervisor considered the idea interesting despite its limited physical footprint because it covers the entire chain from physical sensor to application and adds a measurable comparison of anomaly detection techniques.

**A. Real deployment and sufficient time series:** Identify one actual space where the device may be installed, obtain permission, and gather around **3–6 weeks** of real observations. This should capture daily cycles and differences between weekdays and weekends. User confirmed they have access and can obtain permission, but did not specify the location.

**B. Ground-truth anomalies and evaluation:** To compare detectors meaningfully, know when an actual abnormal condition happened. Safely create and **log** a few controlled anomalies (examples discussed by supervisor: locally warm air near sensor, opening a door; the supervisor also gave a fan-off example, but **do not switch off important equipment cooling**). May inject synthetic events into real data as a separate evaluation track. Report **precision, recall, F1, false alarms per day, and detection delay**.

**C. Escalating comparison of methods:** Compare more than just threshold vs ML:
1. Fixed threshold rules.
2. Temperature rate of change **ΔT/Δt**.
3. Rolling **z-score** and/or **EWMA** statistical detectors.
4. **Isolation Forest** and possibly **Local Outlier Factor (LOF)** if time allows.

Evaluate whether machine learning adds value over simpler methods; improvement is **not assumed**.

**D. Sensor/hardware advice:** Avoid DHT11/DHT22 where possible due to accuracy/stability concerns. Consider SHT31/SHT4x or BME280. A current sensor, door sensor or second air-temperature point was suggested as potential extra dimensions but **the student's chosen scope deliberately excludes extra sensor modules**.

**E. Platform advice:** MQTT with Mosquitto, Python FastAPI, InfluxDB, Docker Compose; UI either Grafana (less bespoke frontend work) or React/Next.js (more development skills).

**F. Committee:** Supervisor proposed κ. Στεφανιδάκης and κ. Ρίγγας; student had no objection.

---

## 5. Hardware shopping decision (Skroutz research, 19 October 2026)

The student explicitly requested **Skroutz parts**, 100% solderless. **These are prior search findings, not proof of current prices, stock, Cyprus delivery, or purchases. Revalidate all listings at checkout.**

| # | Item | Qty | Indicative price then | Notes |
|---|------|----:|----------------------:|-------|
| 1 | ESP32-WROOM-32 USB-C development board | 1 | €6.40 | **Must have factory-installed/soldered male 2.54 mm pin headers** and supported USB-to-serial driver. Exact listing/model must be verified. |
| 2 | **Seeed Grove BME280** sensor board | 1 | €26.00 | ONE physical module with temp, humidity and pressure; Grove 4-pin socket. Confirm genuine BME280 (not BMP280, which lacks humidity). |
| 3 | **Seeed 110990028**, Grove 4-pin to **4 separate female Dupont** jumpers | 1 pack | €4.90 | Makes direct Grove-sensor-to-ESP32 connection without soldering. Check actual pins/pinout. |
| 4 | USB-A to USB-C **data** cable (e.g. Baseus, 1 m) | 1 | €3.99 | Must support data for firmware flashing. Connector must match chosen ESP32. |
| 5 | USB 5 V power adapter suitable for Cyprus UK-type socket | 1 | €2.90 | Only needed if a reliable existing supply isn't available. For weeks-long unattended operation prefer a reputable, certified supply. |
|   | **Indicative subtotal** | | **€44.19** | Excludes shipping and possible mounting/enclosure. |

**Optional later:** ventilated/protective electronics project box (previously considered Gainta G1033B approximately €2.30), cable strain relief and mounting materials; enclosure dimensions/airflow need verification after testing. A small breadboard was originally considered but **is not needed** for the finalized no-solder Grove-to-Dupont setup.

**Compatibility checklist before payment:**

- ESP32 is a **3.3 V-logic** board with **already fitted male headers**, and the listing photographs/specs confirm this; not a bare board requiring solder.
- Sensor is **Grove BME280**, not BMP280 or a BME280 breakout with only unassembled header pins.
- Adapter is the exact **Grove-to-four-female-Dupont** style (**110990028**), not Grove-to-Grove and not male Dupont.
- The 4 jumper connectors fit ESP32 male pins securely.
- Use the correct board USB connector and a true **data-capable** USB cable.
- Confirm shipment to **Cyprus**, including overall cost and shipping dates.
- Choose a stable, safe USB power supply and a protected physical mounting method.

### Indicative I²C wiring (verify actual purchased board/sensor labels first)

| Sensor Grove line | ESP32-WROOM-32 pin |
|-------------------|--------------------|
| VCC | **3V3** |
| GND | **GND** |
| SDA | **GPIO 21** |
| SCL | **GPIO 22** |

**Safety:** Match the *actual wire/pin labeling*, not only assumed wire colors. Power off while wiring. Use **3.3 V I²C voltage levels** for a regular ESP32; verify module specifications. Keep sensor in circulating ambient air, away from ESP32 self-heating, direct exhaust jets, sunlight and inaccessible/unsafe surfaces. Mount wires securely during 3–6 weeks of unattended logging.

---

## 6. Intended system architecture

```text
One real rack / small AV equipment area
          |
  [ONE Grove BME280]
    T, RH, pressure
          | I²C (3V3, GND, SDA, SCL)
     [ONE ESP32]
          | Wi-Fi 2.4 GHz
          | MQTT publish (timestamp, measurements, device ID)
          v
   [Mosquitto MQTT broker]
          |
   [Python data ingestion / FastAPI]
          |
       [InfluxDB]
          |
     +----+-------------------------+
     |                              |
[React Web Dashboard]      [Python anomaly pipeline]
 live/latest readings       thresholds, ΔT/Δt,
 historical charts          rolling z-score, EWMA,
 node-online state          Isolation Forest
 incident/alert log              |
     +-----------< alerts >--------+
```

Use **Docker Compose** to run the locally hosted backend/broker/database reproducibly where practical. Some modules may connect through an MQTT consumer worker rather than FastAPI directly; exact code architecture is not fixed yet.

### Suggested minimum telemetry payload (PROPOSAL, not implemented)

```json
{
  "device_id": "esp32-rack-01",
  "timestamp_utc": "2026-10-27T12:00:00Z",
  "temperature_c": 25.4,
  "relative_humidity_pct": 48.2,
  "pressure_hpa": 1012.7
}
```

Possible MQTT topic: `ptixiaki/equipment-space-01/telemetry`. Include reading timestamps, last-seen status, error/reconnect handling, sensor validation and basic protection against duplicate/missing messages. Set final sampling interval after testing (for example every 30–60 seconds), balancing storage, responsiveness, and detection resolution.

### Expected dashboard capabilities

- Current temperature, humidity (and pressure if used).
- Time-series charts: selectable time windows and normal/detected-anomaly overlays.
- Online/offline state of the **one** ESP32 based on last communication time.
- Clear indication of active alerts plus history/acknowledgment where manageable.
- Simple, legible single-equipment-area interface; **no multi-room admin console required**.
- Responsive web design; optional email notifications, not essential to initial MVP.

---

## 7. Methodology and experiment plan

### Data gathering

- Verify the real location, authorization, Wi-Fi availability, power and whether a computer/server can operate continuously.
- Collect **3–6 weeks** of actual temperature/RH/pressure measurements, recording in UTC while displaying local Cyprus time where appropriate.
- Cover daily operation, inactivity, weekdays and weekends; track any environment/configuration changes in an experiment log.
- Design around intermittent Wi-Fi, power cuts, ESP32 reboot, missing samples and sensor calibration/drift.
- Use physically sensible positioning and document sensor model, sampling interval, location and environmental context.

### Ground-truth anomaly events

- Define a written protocol for each safe test: exact start/end time, type of perturbation, expected sign, observations, and safety constraints.
- Prefer **nonintrusive** techniques such as warm air introduced at a safe distance from the *sensor itself* (not to production equipment) or normal door opening when authorized; avoid wetting electronics, overheating devices, power modifications, or disabling ventilation.
- Label controlled events consistently and separately from naturally observed operational changes.
- Synthetic anomalies may supplement real data, but clearly distinguish synthetic and real evaluations.

### Compare detectors

1. **Fixed thresholds:** baseline high/low temperature and humidity alerts with justifiable thresholds.
2. **Rate-of-change detector:** alert for unusually fast ΔT/Δt; define handling of irregular intervals.
3. **Statistical methods:** rolling z-score and/or EWMA; account for seasonality or day/night variation if data supports it.
4. **Machine learning:** Isolation Forest, optionally LOF; specify training data and scaling/features. Potential features: T, RH, pressure, rates of change, rolling summary statistics, hour-of-day/day-of-week. Prevent future-information leakage in rolling windows.

### Evaluation principles

- Use **chronological train/validation/test splits**, not random splitting of correlated time-series samples.
- Derive baseline parameters on training/validation data; do not tune on held-out test anomalies.
- Clearly define a true-positive **event vs. individual sample**; define acceptable detection window and how repeated alerts are counted.
- Report **precision, recall, F1, false alarms/day, detection delay**; supplement with confusion matrices and limitations if useful.
- Distinguish rare event class imbalance, uncontrolled environmental changes and unknown real-world anomalies.
- It is a valid research result if simpler methods match or beat ML.

### Example thesis demonstration

Live sensor reading → MQTT → database → dashboard; carefully staged nearby temperature change → alert and logged event → compare outputs of multiple detection methods. Do not claim an algorithm has been validated until the experiments are actually run.

---

## 8. Implementation milestones (updated after the software MVP)

- [ ] Confirm official title, committee appointment, and supervisor's expectations.
- [ ] Confirm **written installation permission** and physical placement/power/Wi-Fi/server hosting.
- [ ] Check Skroutz listings, matching connectors, Cypriot shipping, and purchase **one ESP32 + one Grove BME280 + appropriate leads**.
- [ ] Verify power, pinout, flash firmware and read BME280 values via USB serial.
- [ ] ESP32 Wi-Fi connection and MQTT publishing with retries.
- [x] Mosquitto broker and end-to-end ingestion to InfluxDB with a clearly labeled **synthetic publisher**; physical ESP32 ingestion remains pending.
- [x] Docker Compose / FastAPI backend, read APIs and database readiness checks.
- [x] React dashboard with latest/history views, explicit data sources and reading-age status, verified using synthetic data.
- [ ] Dashboard alerts, incident history and acknowledgment behavior.
- [ ] Deployment/monitoring and **3–6 weeks real data**.
- [ ] Controlled experiment log and synthetic anomaly generation where justified.
- [ ] Baseline threshold/rate/statistical detectors.
- [ ] Isolation Forest (LOF optional), fair parameter selection and evaluation.
- [ ] Results, figures, ablation/limitations, university-format dissertation.
- [ ] Final demonstration and presentation.

### Sensible first MVP

**ESP32 → BME280 reading → USB serial → Wi-Fi MQTT → database → basic chart.** Only after this is reliable should the anomaly-detection comparison and polished UI be developed. Software pieces can be prototyped with simulated data before the physical sensor arrives, but simulation must be labeled as such.

---

## 9. Communication and administrative history (condensed)

These details explain why the scope and dates matter; they are **not a substitute for the original email exports**.

- **~22 July 2026:** Initial thesis interest/proposal email prepared for Professor Christopoulou; exact send timestamp should be checked against inbox/sent items.
- **11 August 2026:** Supervisor replied that the idea was interesting and she could supervise, but requested a more precise space, sensor and workload plan, and clarification of ML vs data display.
- **~11 August 2026:** Detailed one-node proposal developed, using ESP32, temperature/humidity, MQTT, web app, storage and anomaly detection; correspondence later confirmed the student sent the detailed proposal.
- **25, 28, 29 September:** Multiple follow-ups about official thesis registration as declarations approached. Student also contacted Department Secretariat and Department President on/around 29 September; student later explicitly confirmed all drafted emails were sent.
- **30 September:** Supervisor reiterated she had agreed to supervise and said she would contact the student the following week to finalize title and committee; discussion about communication delays.
- **12 October:** Friendly reminder about that promised follow-up.
- **13 October:** Supervisor asked for a topic proposal again; student resent the detailed proposal, clarifying it had previously been sent.
- **15 October:** Further friendly reminder.
- **19 October:** Supervisor sent detailed technical feedback, suggested title options and the other committee members. Student planned/answered agreeing with the design while specifying **one ESP32 and one sensor module only**.
- **19 October:** Student reported **official thesis application successfully submitted**.
- **19 October onward:** Hardware selection moved from SHT31 to **Seeed Grove BME280** in Skroutz shopping discussion, with strong preference for **no soldering**.

A prior document called **`Istoriko.pdf`** and a Word file called **`Istoriko_Epikoinonias_Ptyxiaki_Ioannou.docx`** were produced in the original chat as an email chronology. They are **not embedded in this project handoff**. Attach the originals if an administrative task requires verbatim evidence.

---

## 10. Unresolved questions — do not guess

1. **Exact formal title and committee status** as recorded by the University (application successful, formal details not rechecked).
2. **Actual rack/room location**, who grants access, whether **written permission** is finalized.
3. **Exact ESP32 board**, pre-soldered pin headers, exact Grove BME280 board and 110990028 cable availability / shipping to Cyprus.
4. Whether hardware has been ordered **after** this context snapshot; as of snapshot it was **not confirmed purchased**.
5. **Always-on host choice** (laptop, PC, Raspberry Pi, server) and network permissions for MQTT/Web UI.
6. **Acquisition frequency**, accepted environmental alert ranges, and exact perturbation protocol; should be agreed/tested, not made up.
7. Whether pressure is helpful for the comparison or simply displayed/logged.
8. Whether the web UI will be custom React or Grafana fallback, and whether email notification is worth adding.
9. Which algorithms are feasible after inspecting real data and available time; do not claim ML performance in advance.
10. Actual thesis submission deadline, academic formatting instructions, and university progress checkpoints.

---

## 11. Preferences and working instructions for future ChatGPT Work / Codex

- **Language:** Greek (standard, clear and professional) for emails, thesis administration and explanations when the user writes in Greek; technical docs/code and commit messages can be in English unless asked otherwise.
- **User prefers practical, simple-first, step-by-step guidance.** Avoid overengineering and don't add components without a clearly justified need.
- **Respect physical constraints:** one ESP32, one sensor module, no soldering, minimal budget.
- **Prioritize a working end-to-end pipeline** before UI polish or new features.
- **Use reproducible, maintainable code:** separate firmware, ingestion/API, analytics, frontend and infrastructure; choose sensible naming, `.env.example`, README, tests, logs, and Docker Compose where appropriate.
- **Secure by default:** no production passwords, student/employer credentials, Wi-Fi SSIDs/secrets, access tokens, or site-confidential data in code or this file. Use env vars, sample configs and `.gitignore`.
- **Data integrity:** timestamps/units everywhere, timezones explicit, reconnect handling, documented sampling, time-series splits without look-ahead leakage.
- **Research integrity:** be clear about synthetic vs real observations, exact event labels, model limitations, no fabricated metrics.
- **Safe deployment:** do not alter employer rack equipment, mains wiring or cooling; confirm location owner permission and physical/power/network safety.
- **If the user asks to implement:** inspect existing repo files first, then propose/perform the smallest next coherent change; do not assert software or services exist before inspecting them.
- **Ask only truly blocking questions.** If able to proceed with a safe assumption, state it and build a small verifiable prototype.

### Suggested repository layout (illustrative only)

```text
ptixiaki/
├── AGENTS.md                 # Instructions for Codex / coding agents
├── PTIXIAKI_PROJECT_CONTEXT.md
├── README.md
├── firmware/                 # ESP32 + Grove BME280
├── backend/                  # MQTT ingestion, FastAPI, database access
├── analysis/                 # threshold/statistical/ML evaluation
├── frontend/                 # React dashboard
├── infrastructure/           # Docker Compose, broker config, etc.
├── docs/                     # deployment, experiment protocol, thesis notes
├── data/                     # protect raw data; commit only safe samples
├── .env.example
└── .gitignore
```

This layout is a suggestion, **not a claim that any such files already exist**.

---

## 12. Reusable starting prompt in a new project

> Read `PTIXIAKI_PROJECT_CONTEXT.md` in full. We are continuing my Ionian University bachelor's thesis about **one ESP32 + one Grove BME280** for real-room environmental monitoring, MQTT/FastAPI/InfluxDB/React and a rigorous anomaly-detection comparison. The official thesis application has been submitted. Respect the **one-device, one-sensor-module, no-soldering** scope and distinguish planned tasks from completed ones. Start by checking what files/hardware I currently have and help me with the next concrete implementation milestone. Do not assume parts have been bought or the system has been deployed.

---

*Last context update: 27 October 2026. Amend this file as decisions, purchases, deployment approvals, code and experimental results become confirmed.*
