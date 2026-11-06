"""MQTT QoS1 consumer: acknowledge only after a successful synchronous write."""

import logging
import signal
from threading import Event

import paho.mqtt.client as mqtt

from .config import Settings
from .models import parse_payload
from .store import InfluxStore


logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(self, settings: Settings, store, stop_event: Event | None = None):
        self.settings = settings
        self.store = store
        self.stop_event = stop_event or Event()
        self.subscription_failed = False
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
            clean_session=False,
            protocol=mqtt.MQTTv311,
            manual_ack=True,
        )
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(self, client, _userdata, _flags, reason_code, _properties):
        if reason_code.is_failure:
            logger.warning("MQTT connection refused; waiting to reconnect")
            return
        result, _mid = client.subscribe(self.settings.mqtt_topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            logger.error("Unable to request telemetry subscription")
            self.subscription_failed = True
            client.disconnect()

    def on_subscribe(self, client, _userdata, _mid, reason_codes, _properties):
        if any(code.is_failure for code in reason_codes):
            logger.error("MQTT telemetry subscription refused")
            self.subscription_failed = True
            client.disconnect()
        else:
            logger.info("MQTT telemetry subscription ready")

    def on_disconnect(self, _client, _userdata, _flags, reason_code, _properties):
        if not self.stop_event.is_set():
            logger.warning("MQTT disconnected; pending QoS1 messages remain in the broker session")

    @staticmethod
    def acknowledge(client, message):
        if message.qos > 0:
            client.ack(message.mid, message.qos)

    def on_message(self, client, _userdata, message):
        if message.topic != self.settings.mqtt_topic:
            self.acknowledge(client, message)
            return
        try:
            reading = parse_payload(message.payload, self.settings.device_id)
        except ValueError:
            # Malformed messages are poison messages: discard intentionally and
            # acknowledge them. Never log payloads or validation values.
            logger.warning("Discarded invalid telemetry payload")
            self.acknowledge(client, message)
            return

        delay = 1
        while not self.stop_event.is_set():
            try:
                self.store.write(reading)
            except Exception as error:
                logger.warning("Telemetry write failed (%s); retrying without acknowledgement", type(error).__name__)
                if self.stop_event.wait(delay):
                    return
                delay = min(delay * 2, 30)
            else:
                self.acknowledge(client, message)
                return

    def stop(self):
        self.stop_event.set()
        self.client.disconnect()

    def run(self):
        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=30)
        self.client.loop_forever(retry_first_connection=True)
        if self.subscription_failed:
            raise RuntimeError("MQTT telemetry subscription could not be established")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    store = InfluxStore(settings)
    worker = IngestionWorker(settings, store)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda _signum, _frame: worker.stop())
    try:
        worker.run()
    finally:
        worker.stop()
        store.close()


if __name__ == "__main__":
    main()
