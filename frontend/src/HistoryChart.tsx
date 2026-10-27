import { useId } from "react";
import type { Metric, Telemetry } from "./api";

export const METRICS: Record<
  Metric,
  { label: string; unit: string; decimals: number }
> = {
  temperature_c: { label: "Temperature", unit: "°C", decimals: 1 },
  relative_humidity_pct: {
    label: "Relative humidity",
    unit: "% RH",
    decimals: 1,
  },
  pressure_hpa: { label: "Pressure", unit: "hPa", decimals: 1 },
};

export function utcTime(timestamp: string | number) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "UTC",
  }).format(new Date(timestamp));
}

export default function HistoryChart({
  readings,
  metric,
}: {
  readings: Telemetry[];
  metric: Metric;
}) {
  const id = useId();
  if (!readings.length) return null;
  const points = [...readings].sort(
    (a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc),
  );
  const times = points.map((point) => Date.parse(point.timestamp_utc));
  const values = points.map((point) => point[metric]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = Math.max(
    (max - min) * 0.2,
    metric === "pressure_hpa" ? 0.5 : 0.2,
  );
  const low = min - padding;
  const high = max + padding;
  const first = times[0];
  const last = times[times.length - 1];
  const left = 66,
    right = 846,
    top = 24,
    bottom = 256;
  const x = (time: number) =>
    first === last
      ? (left + right) / 2
      : left + ((time - first) / (last - first)) * (right - left);
  const y = (value: number) =>
    bottom - ((value - low) / (high - low)) * (bottom - top);
  const info = METRICS[metric];
  const coordinates = points
    .map((point, index) => `${x(times[index])},${y(point[metric])}`)
    .join(" ");

  return (
    <svg
      className="history-chart"
      viewBox="0 0 870 310"
      role="img"
      aria-labelledby={`${id}-title ${id}-description`}
    >
      <title id={`${id}-title`}>
        {info.label} history in {info.unit}
      </title>
      <desc id={`${id}-description`}>
        {points.length} recorded samples, from {new Date(first).toISOString()}{" "}
        to {new Date(last).toISOString()}. Minimum {min.toFixed(info.decimals)},
        maximum {max.toFixed(info.decimals)} {info.unit}. Horizontal spacing
        represents elapsed time.
      </desc>
      {[0, 1, 2, 3, 4].map((index) => {
        const value = low + ((high - low) * index) / 4;
        return (
          <g key={index}>
            <line
              x1={left}
              x2={right}
              y1={y(value)}
              y2={y(value)}
              className="grid-line"
            />
            <text
              x={left - 14}
              y={y(value) + 4}
              textAnchor="end"
              className="axis-label"
            >
              {value.toFixed(1)}
            </text>
          </g>
        );
      })}
      {points.length > 1 && (
        <polyline points={coordinates} className="reading-line" />
      )}
      {points.map((point, index) => (
        <circle
          key={`${point.timestamp_utc}-${index}`}
          cx={x(times[index])}
          cy={y(point[metric])}
          r={points.length === 1 ? 5 : 2.5}
          className="reading-point"
        >
          <title>
            {utcTime(point.timestamp_utc)} UTC ·{" "}
            {point[metric].toFixed(info.decimals)} {info.unit}
          </title>
        </circle>
      ))}
      <text
        x={first === last ? (left + right) / 2 : left}
        y="286"
        textAnchor={first === last ? "middle" : "start"}
        className="axis-label"
      >
        {utcTime(first)}
      </text>
      {first !== last && (
        <text x={right} y="286" textAnchor="end" className="axis-label">
          {utcTime(last)}
        </text>
      )}
      <text x="846" y="12" textAnchor="end" className="axis-caption">
        {info.unit}
      </text>
    </svg>
  );
}
