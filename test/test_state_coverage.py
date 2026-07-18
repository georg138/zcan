#!/usr/bin/env python3
import asyncio
import unittest
import aiomqtt
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
        async def _collect():
            received = set()
            async with aiomqtt.Client(config["mqtt_host"], config["mqtt_port"]) as client:
                await client.subscribe("lueftung/zehnder/state/+")
                try:
                    async def _drain():
                        async for msg in client.messages:
                            received.add(msg.topic.value)
                    await asyncio.wait_for(_drain(), TIMEOUT)
                except asyncio.TimeoutError:
                    pass
            return received

        cls._received = asyncio.run(_collect())


def _make_state_test(topic):
    def test(self):
        self.assertIn(topic, self._received, f"{topic} was never published")
    return test


for _topic in STATE_TOPICS:
    _name = "test_" + _topic.replace("lueftung/zehnder/state/", "").replace("/", "_")
    setattr(TestStateCoverage, _name, _make_state_test(_topic))

if __name__ == "__main__":
    unittest.main()
