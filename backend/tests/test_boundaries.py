"""Regression tests for queryable timestamps and authenticated readiness."""

from unittest.mock import patch

import pytest

from ptixiaki.config import Settings
from ptixiaki.models import Telemetry
from ptixiaki.store import InfluxStore


@pytest.mark.parametrize("timestamp", ["1970-01-01T00:00:00+02:00", "0001-01-01T00:00:00Z"])
def test_timestamp_before_epoch_is_rejected_after_utc_normalization(timestamp):
    with pytest.raises(ValueError):
        Telemetry(
            device_id="esp32-rack-01",
            timestamp_utc=timestamp,
            temperature_c=25.4,
            relative_humidity_pct=48.2,
            pressure_hpa=1012.7,
            synthetic=True,
        )


def test_readiness_uses_authenticated_query_for_configured_bucket_and_org():
    settings = Settings(influxdb_token="test-token", influxdb_org="configured-org", influxdb_bucket="configured-bucket")
    with patch("ptixiaki.store.InfluxDBClient") as client_class:
        store = InfluxStore(settings)
        assert store.ping() is True
        constructor = client_class.call_args.kwargs
        assert constructor["token"] == "test-token"
        assert constructor["org"] == "configured-org"
        query = store.client.query_api.return_value.query.call_args.args[0]
        assert 'from(bucket: "configured-bucket")' in query
        store.client.ping.assert_not_called()
        store.close()


def test_readiness_propagates_authentication_failure():
    with patch("ptixiaki.store.InfluxDBClient"):
        store = InfluxStore(Settings(influxdb_token="unusable-test-token"))
        store.client.query_api.return_value.query.side_effect = PermissionError("unauthorized")
        with pytest.raises(PermissionError):
            store.ping()
        store.client.ping.assert_not_called()
        store.close()
