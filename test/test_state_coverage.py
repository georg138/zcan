#!/usr/bin/env python3
import time
import unittest
from paho.mqtt import client as mqtt
from config import config
import mapping2 as mapping

TIMEOUT = 30  # seconds — retained messages arrive instantly; window catches slow PDIDs

STATE_TOPICS = {
    "lueftung/zehnder/state/" + v["name"]
    for v in mapping.mapping.values()
}


class TestStateCoverage(unittest.TestCase):
    _received: set = set()

    @classmethod
    def setUpClass(cls):
        received = set()

        def on_message(client, userdata, msg):
            received.add(msg.topic)

        client = mqtt.Client()
        client.connect(config["mqtt_host"], config["mqtt_port"], 60)
        client.subscribe("lueftung/zehnder/state/+")
        client.on_message = on_message
        client.loop_start()
        time.sleep(TIMEOUT)
        client.loop_stop()
        client.disconnect()
        cls._received = received


def _make_state_test(topic):
    def test(self):
        self.assertIn(topic, self._received, f"{topic} was never published")
    return test


for _topic in STATE_TOPICS:
    _name = "test_" + _topic.replace("lueftung/zehnder/state/", "").replace("/", "_")
    setattr(TestStateCoverage, _name, _make_state_test(_topic))

if __name__ == "__main__":
    unittest.main()
