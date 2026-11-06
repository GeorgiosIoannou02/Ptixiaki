# Repository review and remaining work

Review date: **1 November 2026**. Starting revision:
`902580d749e21698a32f08bd13b41aa1a7b47768`.

The repository has a working **synthetic software MVP**. This review covers the
tracked backend, tests, publisher and integration scripts, React dashboard,
container setup and project documentation. It is not a hardware validation or
an assessment of real deployment/research results.

## Improvements in this change

| Finding | Resolution |
| --- | --- |
| Repeated JSON keys silently used the last value, including source provenance | Reject ambiguous messages and test that the worker discards them without writing |
| Sub-microsecond timestamps were silently truncated into the same storage identity | Reject more than six fractional timestamp digits |
| Excessively nested input could escape validation as a parser recursion exception | Treat it as invalid telemetry |
| The browser accepted timezone-free timestamps and malformed status/truncation metadata | Enforce the API's UTC timestamp and metadata contract |
| No way to download a displayed history snapshot | Add CSV download with units, source and explicit truncation metadata |
| Dashboard history cannot supply weeks of raw data | Add a separate, streaming research export for explicit intervals up to 42 days |
| Checks depended on manual execution | Add backend, frontend and Docker pipeline GitHub Actions jobs |
| Credential initialization had no regression coverage | Test private credential creation, preservation, and the existing-database guard |

No concrete infrastructure defect requiring a Compose architecture change was
found. Existing loopback-only ports and explicit synthetic/sensor separation are
preserved. CI uses fresh development credentials and read-only repository
permissions; it does not deploy the project.

## Prioritized completion checklist

### 1. Real sensor acquisition — next physical milestone

- [ ] Confirm the exact ESP32 board, preinstalled headers, Grove BME280 module
  and solderless cable; verify labels, 3.3 V logic and mounting.
- [ ] Read temperature, RH and pressure over USB serial and check physically
  plausible values. Record sensor positioning and ambient comparison limitations.
- [x] Implement generic ESP32-WROOM-32 firmware (6 November; actual board still unconfirmed): I²C error handling, Wi-Fi/MQTT
  reconnects, UTC clock synchronization, configurable acquisition interval and
  explicit `synthetic: false`. Convert pressure to hPa.
- [ ] Test reboot, network loss and time synchronization failures. Decide a bounded
  publisher buffering strategy; preserve acquisition timestamps during retries.
- [ ] Demonstrate real readings through the existing worker/API into Sensor data.

Acceptance: one ESP32 and one module, with traceable real readings and documented
outage behavior. No additional sensor, soldering or equipment control is needed.

### 2. Deployment and collection reliability

- [ ] Obtain written installation permission; confirm safe location, Wi-Fi, power,
  always-on host and responsibility for operations.
- [ ] Configure an approved network path, broker authentication/ACLs and appropriate
  transport protection. The current anonymous, loopback-bound demo is insufficient
  for a remote ESP32. Do not just expose its ports on a public interface.
- [ ] Give API/export and worker only the database permissions they need. Decide
  dashboard authentication/access before exposing it beyond the local machine.
- [ ] Agree sampling cadence, offline threshold, retention and storage budget.
  Keep raw observations throughout collection and evaluation.
- [ ] Establish database backup and restore procedures; test a restore separately.
  CSV export supplements backups but does not replace them.
- [ ] Test host restart, worker/broker restart and database outage recovery. Monitor
  service readiness separately from the age of the last measurement.
- [ ] Collect 3–6 weeks of real readings. Track missing periods, clock corrections,
  device moves, configuration changes and daily coverage in a private log.

Known limits: bounded broker queues, no durable publisher buffer yet, no immutable
raw archive, and conflicting values at one device/source/timestamp overwrite.

### 3. Alerts and experimental ground truth

- [ ] Agree environmental limits using the actual installation and supervisor's
  requirements. Sensor plausibility bounds are not alarm thresholds.
- [ ] Implement thresholds with persistence/hysteresis, then alert transitions,
  incident history and acknowledgment; distinguish stale/unavailable from normal.
- [ ] Record controlled and naturally observed events in a private UTC log with
  event ID, start/end, observation type, protocol, expected effect and uncertainties.
- [ ] Approve safe sensor-local tests and stop conditions. Never disable rack
  cooling, modify electrical systems or apply heat/moisture to production equipment.

Acceptance: repeatable event definitions and auditable labels. Synthetic injections
must remain a separate evaluation track. No arbitrary site thresholds are supplied
by this software review.

### 4. Baselines, ML and thesis results

- [ ] Freeze chronological train/validation/test intervals and label definitions.
  Reserve the test set before tuning any model or threshold.
- [ ] Implement fixed thresholds, ΔT/Δt using actual elapsed time, and causal rolling
  z-score/EWMA with explicit warm-up and missing-data behavior.
- [ ] Fit Isolation Forest on training data only; consider LOF only if justified
  by data/time. Apply the same held-out evaluation to all methods.
- [ ] Define event matching, repeated-alert counting and coverage exclusions.
  Report precision, recall, F1, false alarms/day and detection delay, with explicit
  behavior for zero events, missed detections and unknown labels.
- [ ] Preserve dataset/export hashes, code revision, configurations and random
  seeds; produce reproducible figures and document limitations and negative results.
- [ ] Confirm official title/committee, submission deadline and university format;
  complete dissertation and demonstration from measured results.

ML improvement is a research question, not an implementation promise. Hardware,
permissions, site parameters and experimental observations cannot be inferred
from passing software tests.
