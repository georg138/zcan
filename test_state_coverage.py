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
    def test_all_states_published(self):
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

        missing = STATE_TOPICS - received
        self.assertFalse(
            missing,
            "These state topics were never published:\n" + "\n".join(sorted(missing))
        )


if __name__ == "__main__":
    unittest.main()
