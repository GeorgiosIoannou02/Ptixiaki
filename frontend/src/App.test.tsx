import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Source, Telemetry } from "./api";

const simulated: Telemetry = {
  device_id: "esp32-rack-01",
  timestamp_utc: "2026-10-27T12:00:00Z",
  temperature_c: 25.4,
  relative_humidity_pct: 48.2,
  pressure_hpa: 1012.7,
  synthetic: true,
};

function bodyFor(url: string, source: Source, reading: Telemetry | null) {
  return url.includes("/latest")
    ? { reading, online: !!reading, age_seconds: reading ? 3 : null }
    : {
        readings: reading ? [reading] : [],
        source,
        window: "1h",
        truncated: false,
      };
}

function json(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("dashboard data integrity", () => {
  it("labels simulation and clears simulated values when switching to an empty sensor source", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      const source = url.includes("source=sensor") ? "sensor" : "synthetic";
      return json(
        bodyFor(url, source, source === "synthetic" ? simulated : null),
      );
    });
    vi.stubGlobal("fetch", fetcher);
    render(<App />);

    await screen.findByText("25.4", { selector: "p" });
    expect(screen.getByText("Simulated data")).toBeTruthy();
    expect(screen.getByText("Simulator active")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Sensor" }));

    expect(screen.queryByText("25.4")).toBeNull();
    await screen.findByText("No physical sensor reading received yet.");
    expect(screen.getByText("Physical sensor data")).toBeTruthy();
    expect(screen.queryByText("Simulator active")).toBeNull();
    expect(
      fetcher.mock.calls.some(([url]) => String(url).includes("source=sensor")),
    ).toBe(true);
  });

  it("ignores a late response from the preceding source even if fetch ignores cancellation", async () => {
    const pending: Array<{
      resolve: (value: Response) => void;
      url: string;
      signal: AbortSignal;
    }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>((input, options) => {
        const url = String(input);
        if (url.includes("source=sensor"))
          return Promise.resolve(json(bodyFor(url, "sensor", null)));
        return new Promise((resolve) =>
          pending.push({ resolve, url, signal: options!.signal! }),
        );
      }),
    );
    render(<App />);
    expect(pending).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Sensor" }));
    await screen.findByText("No physical sensor reading received yet.");
    expect(pending.every(({ signal }) => signal.aborted)).toBe(true);
    await act(async () => {
      for (const request of pending)
        request.resolve(json(bodyFor(request.url, "synthetic", simulated)));
    });

    expect(screen.queryByText("25.4")).toBeNull();
    expect(screen.getByText("Physical sensor data")).toBeTruthy();
    expect(screen.getByText("Awaiting readings")).toBeTruthy();
  });

  it("retains readings after a failed refresh and explicitly marks them stale", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) =>
      json(bodyFor(String(input), "synthetic", simulated)),
    );
    vi.stubGlobal("fetch", fetcher);
    render(<App />);
    await screen.findByText("25.4", { selector: "p" });
    fetcher.mockRejectedValue(new Error("Network unavailable"));

    fireEvent.click(screen.getByRole("button", { name: "Refresh readings" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Displayed readings are stale");
    expect(screen.getByText("25.4", { selector: "p" })).toBeTruthy();
    expect(screen.getByText("Connection interrupted")).toBeTruthy();
    expect(screen.getAllByText("Stale reading")).toHaveLength(3);
  });

  it("does not display a sensor response incorrectly returned in simulation mode", async () => {
    const wrongSource = { ...simulated, synthetic: false };
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) =>
        json(bodyFor(String(input), "synthetic", wrongSource)),
      ),
    );
    render(<App />);

    await screen.findByRole("alert");
    expect(screen.queryByText("25.4")).toBeNull();
    expect(screen.getByText("History is unavailable")).toBeTruthy();
  });

  it("aborts outstanding requests when the dashboard is unmounted", async () => {
    const signals: AbortSignal[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>((_input, options) => {
        signals.push(options!.signal!);
        return new Promise(() => {});
      }),
    );
    const view = render(<App />);
    await waitFor(() => expect(signals).toHaveLength(2));
    view.unmount();
    expect(signals.every((signal) => signal.aborted)).toBe(true);
  });
});
