#include "telemetry.h"
#include <cassert>
#include <limits>
#include <iostream>
int main() {
  char out[384];
  assert(telemetry::encode(out, sizeof(out), "esp32-rack-01", "2026-01-01T12:00:00Z", 23.5, 48.25, 101325));
  std::cout << out << '\n';
  assert(!telemetry::validDevice("bad\"id"));
  assert(!telemetry::validDevice("_sensor"));
  assert(!telemetry::validDevice(""));
  assert(!telemetry::validDevice("UPPERCASE"));
  assert(!telemetry::encode(out, 10, "sensor", "2026-01-01T00:00:00Z", 20, 50, 100000));
  assert(!telemetry::valid(std::numeric_limits<float>::quiet_NaN(), 50, 1013));
  assert(!telemetry::valid(20, std::numeric_limits<float>::infinity(), 1013));
  assert(!telemetry::valid(20, 101, 1013));
  assert(!telemetry::valid(86, 50, 1013));
  assert(!telemetry::valid(20, 50, 299));
  assert(telemetry::valid(-40, 0, 300));
  assert(telemetry::valid(85, 100, 1100));
  assert(telemetry::due(10, UINT32_MAX - 10, 20));
  assert(!telemetry::due(10, UINT32_MAX - 10, 22));
}
