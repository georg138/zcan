#!/usr/bin/env python3
import asyncio
import unittest
import aiomqtt
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


async def _send_and_receive(cmd_suffix, cmd_payload, state_topic, expected, reset_payload):
    async with aiomqtt.Client(config["mqtt_host"], config["mqtt_port"]) as client:
        await client.subscribe(state_topic)

        await client.publish("lueftung/zehnder/command/" + cmd_suffix, reset_payload)

        async def _wait_reset():
            async for msg in client.messages:
                if msg.payload.decode().strip() != expected:
                    return

        await asyncio.wait_for(_wait_reset(), TIMEOUT)

        await client.publish("lueftung/zehnder/command/" + cmd_suffix, cmd_payload)

        async def _wait_expected():
            async for msg in client.messages:
                value = msg.payload.decode().strip()
                if value == expected:
                    return value

        return await asyncio.wait_for(_wait_expected(), TIMEOUT)


def _make_test(suffix, payload, state_topic, expected, reset_payload):
    async def test(self):
        value = await _send_and_receive(suffix, payload, state_topic, expected, reset_payload)
        self.assertEqual(value, expected,
            f"expected state '{expected}' on {state_topic}, got '{value}'")
    return test


_cases = {}
for _suffix, _payload, _state_topic, _expected, _reset in COMMAND_EXPECTED:
    _name = "test_%s_%s" % (_suffix, _payload.replace(" ", "_"))
    _cases[_name] = _make_test(_suffix, _payload, _state_topic, _expected, _reset)

TestMqttCommands = type("TestMqttCommands", (unittest.IsolatedAsyncioTestCase,), _cases)

if __name__ == "__main__":
    unittest.main()
