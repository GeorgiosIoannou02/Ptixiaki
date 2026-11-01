import { afterEach, describe, expect, it, vi } from "vitest";
import { downloadHistory, historyCsv } from "./exportCsv";
import type { Telemetry } from "./api";

const sample: Telemetry = {
  device_id: "esp32-rack-01",
  timestamp_utc: "2026-10-27T12:00:00.123456Z",
  temperature_c: 25.4321,
  relative_humidity_pct: 48.2123,
  pressure_hpa: 1012.7123,
  synthetic: true,
};

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("displayed history CSV", () => {
  it("preserves source, truncation, units and precision, in chronological order", () => {
    const csv = historyCsv([
      { ...sample, timestamp_utc: "2026-10-27T13:00:00Z" }, sample,
    ], "synthetic", "6h", true);
    const rows = csv.trim().split("\r\n");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toBe("source,window,window_truncated,device_id,timestamp_utc,temperature_c,relative_humidity_pct,pressure_hpa,synthetic");
    expect(rows[1]).toBe('"synthetic","6h","true","esp32-rack-01","2026-10-27T12:00:00.123456Z","25.4321","48.2123","1012.7123","true"');
    expect(rows[2]).toContain("2026-10-27T13:00:00Z");
  });

  it("keeps real observations explicitly distinct from simulation", () => {
    const csv = historyCsv([{ ...sample, synthetic: false }], "sensor", "1h", false);
    expect(csv).toContain('"sensor","1h","false"');
    expect(csv).toContain('"1012.7123","false"');
  });

  it("starts a named CSV download and releases the temporary browser resource", () => {
    vi.useFakeTimers();
    const createObjectURL = vi.fn((_blob: Blob) => "blob:history-download");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        expect(this.isConnected).toBe(true);
        expect(this.download).toBe("ptixiaki-synthetic-6h-displayed-history.csv");
        expect(this.href).toBe("blob:history-download");
      });
    downloadHistory([sample], "synthetic", "6h", true);
    expect(click).toHaveBeenCalledOnce();
    expect(createObjectURL.mock.calls[0][0].type).toBe("text/csv;charset=utf-8");
    expect(document.querySelector("a[download]")).toBeNull();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:history-download");
  });
});
