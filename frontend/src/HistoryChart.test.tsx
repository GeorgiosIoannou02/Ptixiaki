import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import HistoryChart from "./HistoryChart";
import type { Telemetry } from "./api";

function reading(timestamp_utc: string, temperature_c = 25): Telemetry {
  return {
    timestamp_utc,
    temperature_c,
    device_id: "esp32-rack-01",
    relative_humidity_pct: 48,
    pressure_hpa: 1012,
    synthetic: true,
  };
}

afterEach(cleanup);

describe("history chart", () => {
  it("uses elapsed UTC time for unequal sample spacing rather than equally spaced indexes", () => {
    const { container } = render(
      <HistoryChart
        metric="temperature_c"
        readings={[
          reading("2026-10-27T12:00:00Z"),
          reading("2026-10-27T12:00:10Z"),
          reading("2026-10-27T12:01:40Z"),
        ]}
      />,
    );
    const x = Array.from(container.querySelectorAll("circle")).map((point) =>
      Number(point.getAttribute("cx")),
    );
    expect((x[1] - x[0]) / (x[2] - x[0])).toBeCloseTo(0.1);
    expect(screen.getByRole("img").textContent).toContain(
      "2026-10-27T12:01:40.000Z",
    );
  });

  it("renders one sample as a finite point without inventing a line or trend", () => {
    const { container } = render(
      <HistoryChart
        metric="temperature_c"
        readings={[reading("2026-10-27T12:00:00Z")]}
      />,
    );
    const point = container.querySelector("circle")!;
    expect(Number.isFinite(Number(point.getAttribute("cx")))).toBe(true);
    expect(Number.isFinite(Number(point.getAttribute("cy")))).toBe(true);
    expect(container.querySelector("polyline")).toBeNull();
    expect(screen.getByRole("img").textContent).toContain("1 recorded samples");
  });
});
