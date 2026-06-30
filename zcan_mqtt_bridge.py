#!/usr/bin/env python3

from paho.mqtt import client as mqtt

import mapping2 as mapping
import asyncio
import socket
import struct
import time
import sys
from config import config

can_frame_fmt = "=IB3x8s"

def send_slcan_command(sock, cmd_bytes):
    s = cmd_bytes.decode().strip()
    can_id = int(s[1:9], 16)
    dlc = int(s[9], 16)
    data = list(bytes.fromhex(s[10:10 + dlc * 2]))
    data += [0] * (8 - len(data))
    sock.send(struct.pack("=IB3x8B", can_id | socket.CAN_EFF_FLAG, dlc, *data))

def on_command(client, userdata, message):
    topic_suffix = message.topic.split("/")[-1]
    payload = message.payload.decode().strip()
    key = (topic_suffix, payload)
    cmd_name = mapping.command_topics.get(key)
    if cmd_name is None:
        print("Unknown command: topic=%s payload=%s" % (message.topic, payload), file=sys.stderr)
        return
    cmd_bytes = mapping.command_mapping.get(cmd_name)
    if cmd_bytes is None:
        print("No bytes for command: %s" % cmd_name, file=sys.stderr)
        return
    send_slcan_command(s, cmd_bytes)
    print("Sent command %s" % cmd_name)

mqtt_client = mqtt.Client()
mqtt_client.will_set("lueftung/zehnder/available", "offline", retain=True)
mqtt_client.on_message = on_command
mqtt_client.connect(config['mqtt_host'], config['mqtt_port'], 60)
mqtt_client.subscribe("lueftung/zehnder/command/+")
mqtt_client.loop_start()

def dissect_can_frame(frame):
    can_id, can_dlc, data = struct.unpack(can_frame_fmt, frame)
    if can_id & socket.CAN_RTR_FLAG != 0:
        print("RTR received from %08X"%(can_id&socket.CAN_EFF_MASK))
        return(0,0,[])
    can_id &= socket.CAN_EFF_MASK

    return (can_id, can_dlc, data[:can_dlc])

@asyncio.coroutine
def handle_client(cansocket):
    mqtt_client.publish("lueftung/zehnder/available", "online", retain=True)
    request = None
    while True:
        msg = yield from loop.sock_recv(cansocket, 16)
        can_id, can_dlc, data = dissect_can_frame(msg)
        if can_id & 0xFF800000 == 0:
            pdid = (can_id>>14)&0x7ff
            if pdid in mapping.mapping:
                map = mapping.mapping[pdid]
                topic = "lueftung/zehnder/state/%s" % map["name"]
                info = map["transformation"](data)
                mqtt_client.publish(topic, info, retain=True)
                #print("Pushing to %i %s %s" % (pdid, topic, str(info)))
            else:
                print("Unknown message %i %s" % (pdid, repr(data)), file=sys.stderr)

# create a raw socket and bind it to the given CAN interface
loop = asyncio.get_event_loop()
s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
s.bind((config['can_if'],))
loop.run_until_complete(
        handle_client(s))

# vim: et:sw=4:ts=4:smarttab:foldmethod=indent:si
