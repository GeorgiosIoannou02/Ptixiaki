# Export readings for analysis

The dashboard's **Download CSV** action saves only the displayed history snapshot,
with all three metrics, UTC acquisition timestamps, source, selected window and
`window_truncated` metadata. At most 1,000 points are included. A 24-hour selection
does not guarantee 24 hours of samples at a high sampling frequency.

For a complete interval of up to **42 days**, use the research export CLI from
the repository root, with the local database running:

```bash
uv sync --frozen
uv run --frozen --env-file .env python -m iot_monitor.export \
  --source sensor \
  --start 2026-10-01T00:00:00Z \
  --end 2026-11-01T00:00:00Z \
  --output exports/sensor-october.csv
```

Replace the example dates with the actual collection interval. `--source` is
required; use `synthetic` explicitly for demo data. The configured `DEVICE_ID`
selects the one device. `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG` and
`INFLUXDB_BUCKET` use the same environment settings as the API. This is a local
operator command; no public bulk-download endpoint is added.

- Start is inclusive, end exclusive. Both require a timezone, end cannot be in
  the future, and the interval must be positive and no longer than 42 days.
- Rows are chronological, with no 1,000-point limit, aggregation or imputation.
  CSV columns include device, UTC timestamp, source, synthetic flag and units in
  measurement field names. Microsecond timestamps and stored values are preserved.
- Invalid, mismatched or unordered rows abort the export. A query failure removes
  the temporary file; the final path appears only after the complete query succeeds.
  Existing files, including concurrent exports to the same path, are never replaced.
- Files are created with owner-only permissions. Use `exports/`, which is
  ignored by Git and separate from Docker-managed database directories. An empty
  interval produces a header-only CSV and reports zero rows.
- The output filesystem must support hard links for atomic creation without
  replacement. A failure returns a nonzero exit code and does not publish a partial
  CSV. Keep sufficient free disk space for the selected interval.

This is an export of the current database, **not an immutable raw-message archive
or a database backup**. Late telemetry and conflicting writes with the same point
identity can change a repeated export. Record the command, export time, repository
commit, sampling settings and file SHA-256 in your private experiment records.
For adjacent chunks use the preceding end as the next start, and keep sources
separate. Preserve the original CSV before cleaning or labeling it. Successful
export alone establishes neither complete acquisition nor research validity.

## Before detector evaluation

Check coverage, gaps, duplicates, clock corrections and environmental changes.
Keep UTC ground-truth event labels separate from detector outputs. Split data
chronologically; fit scalers, thresholds and model parameters on training and
validation periods only. Do not fill missing values using future observations.
See [the remaining work](review-and-roadmap.md) for the collection and evaluation
acceptance criteria.
