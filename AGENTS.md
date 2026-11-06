# Coding-agent instructions — IoT Environmental Monitoring System for Equipment Spaces with Anomaly Detection

**Read `PROJECT_CONTEXT.md` completely before designing or implementing anything.** It is the project source of truth for current scope, thesis requirements, status and unresolved decisions.

## Non-negotiable scope
- Exactly **one ESP32** and **one Seeed Grove BME280** sensor module (temperature, humidity, pressure). No second physical sensor, multi-node hardware, custom PCB, or soldering unless the user explicitly changes scope.
- Hardware purchases, site permissions and physical deployment remain unconfirmed. A synthetic software MVP is now implemented; read the implementation update in `PROJECT_CONTEXT.md` and inspect files before extending it.
- The software review adds strict telemetry validation, CSV snapshot/research exports and CI. Read `docs/review-and-roadmap.md` for remaining milestones; neither CSV export nor CI establishes real collection or detector validation.
- The research question is whether ML adds value beyond thresholds, ΔT/Δt, rolling z-score/EWMA on **3–6 weeks of real time-series data** with ethically/safely induced and logged anomalies.
- Prioritize minimal reproducible end-to-end pipeline: ESP32 → MQTT Mosquitto → Python/FastAPI + InfluxDB → React dashboard → evaluation.

## Implementation principles
- Keep units and UTC timestamps explicit; validate sensor readings and handle disconnect/retry cases.
- Do not accidentally leak future samples into rolling features or time-series train/test splitting.
- Secure secrets via environment variables; never commit credentials or sensitive site information.
- Keep architecture modular and documented, with tests and small measurable milestones.
- Avoid unsafe experiments on production AV equipment or modifications of electrical/cooling systems.
- Clearly distinguish implemented facts, user confirmations, assumptions, and proposed options.

## Workflow
1. Inspect existing project files/changes before modifying code.
2. Review the open decisions in `PROJECT_CONTEXT.md`.
3. Implement and verify the smallest next useful increment.
4. Update the project README/checklist and this handoff file when milestones are actually completed.

For emails to the supervisor and university, use professional **Greek**. For source code and technical docs, English is fine.

