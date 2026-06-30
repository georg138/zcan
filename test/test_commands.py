#!/usr/bin/env python3
import time
import threading
import unittest
from paho.mqtt import client as mqtt
from config import config

TIMEOUT = 5  # seconds to wait for device response

COMMAND_EXPECTED = [
    # (suffix, payload, state_topic, expected_value, reset_payload)
    ("set_ventilation_level", "0", "lueftung/zehnder/state/ventilation_level", "0.0", "3"),
    ("set_ventilation_level", "1", "lueftung/zehnder/state/ventilation_level", "1.0", "0"),
    ("set_ventilation_level", "2", "lueftung/zehnder/state/ventilation_level", "2.0", "0"),
    ("set_ventilation_level", "3", "lueftung/zehnder/state/ventilation_level", "3.0", "0"),
    ("operating_mode", "auto",   "lueftung/zehnder/state/operating_mode", "auto",           "manual"),
    ("operating_mode", "manual", "lueftung/zehnder/state/operating_mode", "limited manual", "auto"),
    ("bypass", "auto",  "lueftung/zehnder/state/bypass_state", "auto",  "open"),
    ("bypass", "open",  "lueftung/zehnder/state/bypass_state", "open",  "auto"),
    ("bypass", "close", "lueftung/zehnder/state/bypass_state", "close", "auto"),
    ("temperature_profile", "normal", "lueftung/zehnder/state/comfocool_profile", "0", "cool"),
    ("temperature_profile", "cool",   "lueftung/zehnder/state/comfocool_profile", "1", "normal"),
    ("temperature_profile", "warm",   "lueftung/zehnder/state/comfocool_profile", "2", "normal"),
    ("menu", "basis",    "lueftung/zehnder/state/current_menu_mode", "1", "extended"),
    ("menu", "extended", "lueftung/zehnder/state/current_menu_mode", "2", "basis"),
]


def _send_and_receive(cmd_suffix, cmd_payload, state_topic, expected, reset_payload):
    reset_done = threading.Event()
    received = threading.Event()
    result = {}

    def on_message(client, userdata, msg):
        value = msg.payload.decode().strip()
        if not reset_done.is_set():
            if value != expected:
                reset_done.set()
        else:
            if value == expected:
                result["value"] = value
                received.set()

    client = mqtt.Client()
    client.connect(config["mqtt_host"], config["mqtt_port"], 60)
    client.subscribe(state_topic)
    client.on_message = on_message
    client.loop_start()
    time.sleep(0.2)

    client.publish("lueftung/zehnder/command/" + cmd_suffix, reset_payload)
    reset_done.wait(timeout=TIMEOUT)

    client.publish("lueftung/zehnder/command/" + cmd_suffix, cmd_payload)
    received.wait(timeout=TIMEOUT)

    client.loop_stop()
    client.disconnect()
    return result.get("value")


def _make_test(suffix, payload, state_topic, expected, reset_payload):
    def test(self):
        value = _send_and_receive(suffix, payload, state_topic, expected, reset_payload)
        self.assertEqual(value, expected,
            f"expected state '{expected}' on {state_topic}, got '{value}'")
    return test


_cases = {}
for _suffix, _payload, _state_topic, _expected, _reset in COMMAND_EXPECTED:
    _name = "test_%s_%s" % (_suffix, _payload.replace(" ", "_"))
    _cases[_name] = _make_test(_suffix, _payload, _state_topic, _expected, _reset)

TestMqttCommands = type("TestMqttCommands", (unittest.TestCase,), _cases)

if __name__ == "__main__":
    unittest.main()
