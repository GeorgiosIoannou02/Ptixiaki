import { useState } from "react";
import type { Metric, Source, TimeWindow } from "./api";
import HistoryChart, { METRICS, utcTime } from "./HistoryChart";
import { useReadings } from "./useReadings";

function ageLabel(seconds: number | null) {
  if (seconds === null) return "No reading received";
  if (seconds < 60) return `${Math.max(0, Math.floor(seconds))}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function MetricIcon({ metric }: { metric: Metric }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {metric === "temperature_c" ? (
        <>
          <path d="M9 14.8V5a3 3 0 0 1 6 0v9.8a5 5 0 1 1-6 0Z" />
          <path d="M12 8v10" />
          <circle cx="12" cy="18" r="1.3" />
        </>
      ) : metric === "relative_humidity_pct" ? (
        <path d="M12 3s-7 7.5-7 12a7 7 0 0 0 14 0c0-4.5-7-12-7-12Zm-3 13a3 3 0 0 0 3 3" />
      ) : (
        <>
          <path d="M5 18a9 9 0 1 1 14 0" />
          <path d="m12 13 4-5M4 13h2m12 0h2M12 4v2" />
          <circle cx="12" cy="13" r="1.5" />
        </>
      )}
    </svg>
  );
}

export default function App() {
  const [source, setSource] = useState<Source>("synthetic");
  const [window, setWindow] = useState<TimeWindow>("1h");
  const [metric, setMetric] = useState<Metric>("temperature_c");
  const state = useReadings(source, window);
  const reading = state.latest.reading;
  const ageSeconds =
    state.latest.age_seconds === null
      ? null
      : state.latest.age_seconds +
        (state.updatedAt === null
          ? 0
          : Math.max(0, Date.now() - state.updatedAt) / 1000);
  const status = state.error
    ? "Connection interrupted"
    : state.loading
      ? "Connecting"
      : !reading
        ? "Awaiting readings"
        : state.latest.online
          ? source === "synthetic"
            ? "Simulator active"
            : "Sensor online"
          : "No recent readings";
  const date = reading
    ? new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(new Date(reading.timestamp_utc))
    : null;

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="wordmark" href="/" aria-label="PTIXIAKI home">
          <span className="brand-mark" aria-hidden="true">
            p.
          </span>{" "}
          PTIXIAKI
        </a>
        <span className="header-caption">
          Environmental monitoring <span className="header-divider">/</span>{" "}
          Thesis prototype
        </span>
      </header>

      <main>
        <section className="page-heading" aria-labelledby="page-title">
          <div>
            <p className="eyebrow">ONE DEVICE · THREE MEASUREMENTS</p>
            <h1 id="page-title">A closer look at the environment.</h1>
            <p className="intro">
              Temperature, humidity, and pressure from one monitoring point.
            </p>
          </div>
          <div className="source-control">
            <span id="source-label" className="control-label">
              Data source
            </span>
            <div
              className="segmented"
              role="group"
              aria-labelledby="source-label"
            >
              <button
                type="button"
                aria-pressed={source === "synthetic"}
                onClick={() => setSource("synthetic")}
              >
                Simulation
              </button>
              <button
                type="button"
                aria-pressed={source === "sensor"}
                onClick={() => setSource("sensor")}
              >
                Sensor
              </button>
            </div>
          </div>
        </section>

        <div
          className={`source-note ${source === "synthetic" ? "synthetic" : "sensor"}`}
        >
          <span className="note-symbol" aria-hidden="true">
            {source === "synthetic" ? "◌" : "◎"}
          </span>
          <div>
            <strong>
              {source === "synthetic"
                ? "Simulated data"
                : "Physical sensor data"}
            </strong>
            <span>
              {source === "synthetic"
                ? "For testing the software pipeline. These readings are not environmental observations."
                : "Only readings explicitly marked as real are shown. Hardware and deployment must be verified separately."}
            </span>
          </div>
        </div>

        {state.error && (
          <div className="error-notice" role="alert">
            <strong>Could not refresh readings.</strong>{" "}
            {reading
              ? "Displayed readings are stale; their last recorded values are retained."
              : "The service may be unavailable. No readings are being substituted."}{" "}
            Retrying automatically.
          </div>
        )}

        <section className="readings-section" aria-labelledby="readings-title">
          <div className="section-bar">
            <div className="section-label">
              <h2 id="readings-title">Latest reading</h2>
              <span
                className={`connection-status ${state.error || !state.latest.online ? "muted" : ""}`}
                role="status"
              >
                <i aria-hidden="true" />
                {status}
              </span>
            </div>
            <button
              type="button"
              className="refresh-button"
              onClick={state.refresh}
              disabled={state.refreshing}
              aria-label="Refresh readings"
            >
              <svg
                className={state.refreshing ? "rotating" : ""}
                width="15"
                height="15"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                aria-hidden="true"
              >
                <path d="M16 7a6.5 6.5 0 1 0 .5 5M16 3v4h-4" />
              </svg>
              {state.refreshing ? "Refreshing" : "Refresh"}
            </button>
          </div>
          <div
            className={`metric-grid ${state.error ? "stale" : ""}`}
            aria-busy={state.loading}
          >
            {(Object.keys(METRICS) as Metric[]).map((key) => (
              <article
                className={`metric-card ${metric === key ? "selected" : ""}`}
                key={key}
              >
                <div className="metric-heading">
                  <h3>{METRICS[key].label}</h3>
                  <MetricIcon metric={key} />
                </div>
                <p className="metric-value">
                  {reading ? reading[key].toFixed(METRICS[key].decimals) : "—"}
                  <span>{METRICS[key].unit}</span>
                </p>
                <p className="metric-detail">
                  {state.error && reading
                    ? "Stale reading"
                    : reading
                      ? source === "synthetic"
                        ? "Simulated measurement"
                        : "Grove BME280 measurement"
                      : state.loading
                        ? "Loading readings…"
                        : "Waiting for the first sample"}
                </p>
              </article>
            ))}
          </div>
          <div className="reading-meta">
            <span>
              {reading ? (
                <>
                  <span className="mono">{reading.device_id}</span>
                  <span className="meta-dot">·</span>
                  {date}, {utcTime(reading.timestamp_utc)} UTC
                </>
              ) : source === "synthetic" ? (
                "Start the simulator to send the first reading."
              ) : (
                "No physical sensor reading received yet."
              )}
            </span>
            <span>{ageLabel(ageSeconds)}</span>
          </div>
        </section>

        <section className="history-panel" aria-labelledby="history-title">
          <div className="history-heading">
            <div>
              <p className="eyebrow">RECORDED SAMPLES</p>
              <h2 id="history-title">Reading history</h2>
            </div>
            <div className="chart-controls">
              <label>
                <span className="sr-only">Chart measurement</span>
                <select
                  value={metric}
                  onChange={(event) => setMetric(event.target.value as Metric)}
                >
                  {(Object.keys(METRICS) as Metric[]).map((key) => (
                    <option key={key} value={key}>
                      {METRICS[key].label}
                    </option>
                  ))}
                </select>
              </label>
              <div
                className="segmented compact"
                role="group"
                aria-label="History window"
              >
                {(["1h", "6h", "24h"] as TimeWindow[]).map((value) => (
                  <button
                    type="button"
                    key={value}
                    aria-pressed={window === value}
                    onClick={() => setWindow(value)}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {state.readings.length ? (
            <HistoryChart readings={state.readings} metric={metric} />
          ) : (
            <div className="empty-chart" role="status">
              <svg
                width="44"
                height="36"
                viewBox="0 0 44 36"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.3"
                aria-hidden="true"
              >
                <path d="M3 2v30h38M9 23l8-7 7 3 11-10" />
                <circle cx="35" cy="9" r="2" />
              </svg>
              <h3>
                {state.loading
                  ? "Loading the history…"
                  : state.error
                    ? "History is unavailable"
                    : "The first reading starts the story."}
              </h3>
              <p>
                {state.loading
                  ? "Retrieving recorded measurements."
                  : state.error
                    ? "Check the service connection, then refresh."
                    : source === "synthetic"
                      ? "Run the simulator to see measurements arrive here."
                      : "Sensor history will appear after real readings are received."}
              </p>
            </div>
          )}
          <div className="chart-footer">
            <span>
              <i className="legend-dot" aria-hidden="true" />
              {METRICS[metric].label}
              <span className="meta-dot">·</span>
              {state.readings.length}{" "}
              {state.readings.length === 1 ? "sample" : "samples"}
              {state.error && state.readings.length > 0
                ? " · Stale history"
                : ""}
            </span>
            <span>Time shown in UTC</span>
          </div>
          {state.truncated && (
            <p className="truncated-note">
              Showing the most recent 1,000 samples in this window. Choose a
              shorter window for more detail.
            </p>
          )}
        </section>

        <footer className="page-footer">
          <p>
            <span className="footer-label">Research in progress</span> Anomaly
            detection and alert evaluation are planned.
          </p>
          <span>One ESP32 + one Grove BME280</span>
        </footer>
      </main>
    </div>
  );
}
