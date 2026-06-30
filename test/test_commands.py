#!/usr/bin/env python3
import time
import threading
import unittest
from paho.mqtt import client as mqtt
from config import config

TIMEOUT = 5  # seconds to wait for device response

COMMAND_EXPECTED = [
    # (command_topic_suffix, payload, expected_state_topic, expected_value)
    ("set_ventilation_level", "0", "lueftung/zehnder/state/ventilation_level", "0.0"),
    ("set_ventilation_level", "1", "lueftung/zehnder/state/ventilation_level", "1.0"),
    ("set_ventilation_level", "2", "lueftung/zehnder/state/ventilation_level", "2.0"),
    ("set_ventilation_level", "3", "lueftung/zehnder/state/ventilation_level", "3.0"),
    ("operating_mode", "auto",   "lueftung/zehnder/state/operating_mode", "auto"),
    ("operating_mode", "manual", "lueftung/zehnder/state/operating_mode", "limited manual"),
    ("bypass", "auto",  "lueftung/zehnder/state/bypass_state", "auto"),
    ("bypass", "open",  "lueftung/zehnder/state/bypass_state", "open"),
    ("bypass", "close", "lueftung/zehnder/state/bypass_state", "close"),
    ("temperature_profile", "normal", "lueftung/zehnder/state/comfocool_profile", "0"),
    ("temperature_profile", "cool",   "lueftung/zehnder/state/comfocool_profile", "1"),
    ("temperature_profile", "warm",   "lueftung/zehnder/state/comfocool_profile", "2"),
    ("menu", "basis",    "lueftung/zehnder/state/current_menu_mode", "1"),
    ("menu", "extended", "lueftung/zehnder/state/current_menu_mode", "2"),
]


def _send_and_receive(cmd_suffix, cmd_payload, state_topic, expected):
    received = threading.Event()
    result = {}

    def on_message(client, userdata, msg):
        value = msg.payload.decode().strip()
        if value == expected:
            result["value"] = value
            received.set()

    client = mqtt.Client()
    client.connect(config["mqtt_host"], config["mqtt_port"], 60)
    client.subscribe(state_topic)
    client.on_message = on_message
    client.loop_start()
    time.sleep(0.2)
    client.publish("lueftung/zehnder/command/" + cmd_suffix, cmd_payload)
    received.wait(timeout=TIMEOUT)
    client.loop_stop()
    client.disconnect()
    return result.get("value")


def _make_test(suffix, payload, state_topic, expected):
    def test(self):
        value = _send_and_receive(suffix, payload, state_topic, expected)
        self.assertEqual(value, expected,
            f"expected state '{expected}' on {state_topic}, got '{value}'")
    return test


_cases = {}
for _suffix, _payload, _state_topic, _expected in COMMAND_EXPECTED:
    _name = "test_%s_%s" % (_suffix, _payload.replace(" ", "_"))
    _cases[_name] = _make_test(_suffix, _payload, _state_topic, _expected)

TestMqttCommands = type("TestMqttCommands", (unittest.TestCase,), _cases)

if __name__ == "__main__":
    unittest.main()
