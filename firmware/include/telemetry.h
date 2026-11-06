#pragma once
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdint>

namespace telemetry {
inline bool validDevice(const char *id) {
  const size_t n = std::strlen(id);
  if (!n || n > 64) return false;
  for (size_t i = 0; i < n; ++i) {
    const char c = id[i];
    if (!(c >= 'a' && c <= 'z') && !(c >= '0' && c <= '9') &&
        !(i && (c == '-' || c == '_'))) return false;
  }
  return true;
}
inline bool valid(float t, float h, float p) {
  return std::isfinite(t) && std::isfinite(h) && std::isfinite(p) &&
         t >= -40 && t <= 85 && h >= 0 && h <= 100 && p >= 300 && p <= 1100;
}
inline bool due(uint32_t now, uint32_t last, uint32_t interval) {
  return static_cast<uint32_t>(now - last) >= interval;
}
// timestamp is produced internally by strftime, never from user input.
inline bool encode(char *out, size_t size, const char *id, const char *timestamp,
                   float t, float h, float pressurePa) {
  const float p = pressurePa / 100.0f;
  if (!validDevice(id) || !valid(t, h, p)) return false;
  const int n = std::snprintf(out, size,
      "{\"device_id\":\"%s\",\"timestamp_utc\":\"%s\","
      "\"temperature_c\":%.3f,\"relative_humidity_pct\":%.3f,"
      "\"pressure_hpa\":%.3f,\"synthetic\":false}", id, timestamp, t, h, p);
  return n > 0 && static_cast<size_t>(n) < size;
}
}
