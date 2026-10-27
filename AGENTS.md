# Coding-agent instructions — PTIXIAKI

**Read `PTIXIAKI_PROJECT_CONTEXT.md` completely before designing or implementing anything.** It is the project source of truth for current scope, thesis requirements, status and unresolved decisions.

## Non-negotiable scope
- Exactly **one ESP32** and **one Seeed Grove BME280** sensor module (temperature, humidity, pressure). No second physical sensor, multi-node hardware, custom PCB, or soldering unless the user explicitly changes scope.
- No confirmed hardware purchases, working code, site permissions or deployment as of the 27 Oct 2026 snapshot. Inspect files and ask for status updates as needed.
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
2. Review the open decisions in `PTIXIAKI_PROJECT_CONTEXT.md`.
3. Implement and verify the smallest next useful increment.
4. Update the project README/checklist and this handoff file when milestones are actually completed.

For emails to the supervisor and university, use professional **Greek**. For source code and technical docs, English is fine.
