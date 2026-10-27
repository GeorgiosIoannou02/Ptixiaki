import { useEffect, useRef, useState } from "react";
import { readSnapshot } from "./api";
import type { LatestReading, Source, Telemetry, TimeWindow } from "./api";

interface Snapshot {
  source: Source;
  window: TimeWindow;
  latest: LatestReading;
  readings: Telemetry[];
  truncated: boolean;
  loading: boolean;
  refreshing: boolean;
  error: boolean;
  updatedAt: number | null;
}

const emptySnapshot = (source: Source, window: TimeWindow): Snapshot => ({
  source,
  window,
  latest: { reading: null, online: false, age_seconds: null },
  readings: [],
  truncated: false,
  loading: true,
  refreshing: true,
  error: false,
  updatedAt: null,
});

export function useReadings(source: Source, window: TimeWindow) {
  const [snapshot, setSnapshot] = useState(() => emptySnapshot(source, window));
  const refreshRef = useRef<() => void>(() => {});

  useEffect(() => {
    let disposed = false;
    let request = 0;
    let activeController: AbortController | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setSnapshot(emptySnapshot(source, window));

    const refresh = async () => {
      clearTimeout(timer);
      const currentRequest = ++request;
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      const timeout = setTimeout(() => controller.abort(), 8000);
      setSnapshot((previous) => ({ ...previous, refreshing: true }));
      try {
        const { latest, history } = await readSnapshot(
          source,
          window,
          controller.signal,
        );
        if (disposed || request !== currentRequest) return;
        setSnapshot({
          source,
          window,
          latest,
          readings: history.readings,
          truncated: history.truncated === true,
          loading: false,
          refreshing: false,
          error: false,
          updatedAt: Date.now(),
        });
      } catch {
        if (disposed || request !== currentRequest) return;
        setSnapshot((previous) => ({
          ...previous,
          loading: false,
          refreshing: false,
          error: true,
        }));
      } finally {
        clearTimeout(timeout);
        if (!disposed && request === currentRequest)
          timer = setTimeout(() => void refresh(), 5000);
      }
    };

    refreshRef.current = () => void refresh();
    void refresh();
    return () => {
      disposed = true;
      request += 1;
      clearTimeout(timer);
      activeController?.abort();
    };
  }, [source, window]);

  // Never render the preceding source under a newly selected source label.
  const current =
    snapshot.source === source && snapshot.window === window
      ? snapshot
      : emptySnapshot(source, window);
  return { ...current, refresh: () => refreshRef.current() };
}
