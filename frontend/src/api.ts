export type Source = "synthetic" | "sensor";
export type TimeWindow = "1h" | "6h" | "24h";
export type Metric = "temperature_c" | "relative_humidity_pct" | "pressure_hpa";

export interface Telemetry {
  device_id: string;
  timestamp_utc: string;
  temperature_c: number;
  relative_humidity_pct: number;
  pressure_hpa: number;
  synthetic: boolean;
}

export interface LatestReading {
  reading: Telemetry | null;
  online: boolean;
  age_seconds: number | null;
}

export interface History {
  readings: Telemetry[];
  source: Source;
  window: TimeWindow;
  truncated: boolean;
}

function validReading(value: unknown, source: Source): value is Telemetry {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.device_id === "string" &&
    /^[a-z0-9][a-z0-9_-]{0,63}$/.test(item.device_id) &&
    typeof item.timestamp_utc === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(item.timestamp_utc) &&
    Number.isFinite(Date.parse(item.timestamp_utc)) &&
    item.synthetic === (source === "synthetic") &&
    ["temperature_c", "relative_humidity_pct", "pressure_hpa"].every(
      (field) =>
        typeof item[field] === "number" && Number.isFinite(item[field]),
    )
  );
}

async function readJson(path: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(path, {
    signal,
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

export async function readSnapshot(
  source: Source,
  window: TimeWindow,
  signal: AbortSignal,
) {
  const [latestValue, historyValue] = await Promise.all([
    readJson(`/api/readings/latest?source=${source}`, signal),
    readJson(`/api/readings?source=${source}&window=${window}`, signal),
  ]);
  const latest = latestValue as LatestReading;
  const history = historyValue as History;
  if (
    !latest ||
    typeof latest.online !== "boolean" ||
    !(
      latest.age_seconds === null ||
      (typeof latest.age_seconds === "number" &&
        Number.isFinite(latest.age_seconds) && latest.age_seconds >= 0)
    ) ||
    !(latest.reading === null || validReading(latest.reading, source)) ||
    (latest.reading === null && (latest.online || latest.age_seconds !== null)) ||
    (latest.reading !== null && latest.age_seconds === null) ||
    !history ||
    history.source !== source ||
    history.window !== window ||
    typeof history.truncated !== "boolean" ||
    !Array.isArray(history.readings) ||
    history.readings.length > 1000 ||
    !history.readings.every((reading) => validReading(reading, source))
  ) {
    throw new Error("Invalid telemetry response");
  }
  return { latest, history };
}

