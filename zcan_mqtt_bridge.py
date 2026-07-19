#!/usr/bin/env python3

from paho.mqtt import client as mqtt

import mapping2 as mapping
import ComfoNetCan as CN
import asyncio
import socket
import struct
import sys
from config import config

can_frame_fmt = "=IB3x8s"

def send_command(cnet, hex_str):
    cnet.write_CN_Msg(0x11, cnet.ComfoAddr, 1, 0, 1, list(bytes.fromhex(hex_str)))

def on_command(client, userdata, message):
    topic_suffix = message.topic.split("/")[-1]
    payload = message.payload.decode().strip()
    key = (topic_suffix, payload)
    cmd_name = mapping.command_topics.get(key)
    if cmd_name is None:
        print("Unknown command: topic=%s payload=%s" % (message.topic, payload), file=sys.stderr)
        return
    data = mapping.command_mapping.get(cmd_name)
    if data is None:
        print("No data for command: %s" % cmd_name, file=sys.stderr)
        return
    send_command(cnet, data)
    print("Sent command %s" % cmd_name)

# create a raw socket and bind it to the given CAN interface
s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
s.bind((config['can_if'],))
s.setblocking(False)
cnet = CN.ComfoNet(s)
cnet.FindComfoAirQ()

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

async def handle_client(cansocket):
    loop = asyncio.get_running_loop()
    mqtt_client.publish("lueftung/zehnder/available", "online", retain=True)
    while True:
        msg = await loop.sock_recv(cansocket, 16)
        can_id, can_dlc, data = dissect_can_frame(msg)
        if can_id & 0xFF800000 == 0:
            pdid = (can_id >> 14) & 0x7ff
            if pdid in mapping.mapping:
                map = mapping.mapping[pdid]
                topic = "lueftung/zehnder/state/%s" % map["name"]
                info = map["transformation"](data)
                mqtt_client.publish(topic, info, retain=True)
            else:
                print("Unknown message %i %s" % (pdid, repr(data)), file=sys.stderr)

asyncio.run(handle_client(s))

# vim: et:sw=4:ts=4:smarttab:foldmethod=indent:si
