import type { Source, Telemetry, TimeWindow } from "./api";

function csvCell(value: string | number | boolean) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

// Export exactly the displayed snapshot, never imply a complete research dataset.
export function historyCsv(
  readings: Telemetry[],
  source: Source,
  window: TimeWindow,
  truncated: boolean,
) {
  const columns = [
    "source", "window", "window_truncated", "device_id", "timestamp_utc",
    "temperature_c", "relative_humidity_pct", "pressure_hpa", "synthetic",
  ];
  const rows = [...readings]
    .sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc))
    .map((reading) => [
      source, window, truncated, reading.device_id, reading.timestamp_utc,
      reading.temperature_c, reading.relative_humidity_pct, reading.pressure_hpa,
      reading.synthetic,
    ].map(csvCell).join(","));
  return [columns.join(","), ...rows].join("\r\n") + "\r\n";
}

export function downloadHistory(
  readings: Telemetry[],
  source: Source,
  window: TimeWindow,
  truncated: boolean,
) {
  const url = URL.createObjectURL(new Blob(
    [historyCsv(readings, source, window, truncated)],
    { type: "text/csv;charset=utf-8" },
  ));
  const link = document.createElement("a");
  link.href = url;
  link.download = `iot-monitor-${source}-${window}-displayed-history.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Allow the browser to start consuming the download before releasing its URL.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
