import { afterEach, describe, expect, it, vi } from "vitest";
import { readSnapshot } from "./api";

const reading = {
  device_id: "esp32-rack-01", timestamp_utc: "2026-10-27T12:00:00Z",
  temperature_c: 25, relative_humidity_pct: 48, pressure_hpa: 1012, synthetic: true,
};

function fetchSnapshot(latest: unknown, history: unknown) {
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (url) => new Response(
    JSON.stringify(String(url).includes("/latest") ? latest : history),
    { status: 200, headers: { "Content-Type": "application/json" } },
  )));
  return readSnapshot("synthetic", "1h", new AbortController().signal);
}

afterEach(() => vi.unstubAllGlobals());

describe("telemetry response validation", () => {
  const history = { source: "synthetic", window: "1h", truncated: false, readings: [reading] };
  const latest = { reading, age_seconds: 3, online: true };

  it("rejects timezone-free timestamps instead of treating local time as UTC", async () => {
    await expect(fetchSnapshot({ ...latest, reading: { ...reading, timestamp_utc: "2026-10-27T12:00:00" } }, history))
      .rejects.toThrow("Invalid telemetry response");
  });

  it.each([-1, null])("rejects invalid reading age %s", async (age_seconds) => {
    await expect(fetchSnapshot({ ...latest, age_seconds }, history))
      .rejects.toThrow("Invalid telemetry response");
  });

  it("rejects an online status without any reading", async () => {
    await expect(fetchSnapshot({ reading: null, online: true, age_seconds: null }, history))
      .rejects.toThrow("Invalid telemetry response");
  });

  it("rejects ambiguous truncation metadata", async () => {
    await expect(fetchSnapshot(latest, { ...history, truncated: "true" }))
      .rejects.toThrow("Invalid telemetry response");
  });

  it("rejects device identifiers outside the telemetry contract", async () => {
    await expect(fetchSnapshot({ ...latest, reading: { ...reading, device_id: "=SUM(1,2)" } }, history))
      .rejects.toThrow("Invalid telemetry response");
  });
});
