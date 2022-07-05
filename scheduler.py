#!/usr/bin/env python3
import schedule
import time
import os
import sys

import broadlink
from broadlink.const import DEFAULT_PORT
from broadlink.exceptions import ReadError, StorageError

def setup(device):
    fd = open(os.path.join(sys.path[0], "data", device), "r+t")
    values = fd.read().split()
    print (values)
    
    devtype = int(values[0], 0)
    host = values[1]
    mac = bytearray.fromhex(values[2])

    dev = broadlink.gendevice(devtype, (host, DEFAULT_PORT), mac)
    dev.auth()
    return dev

def send_single (action):
    if (not action):
        print("Nothing to do")
        return
    fd = open(os.path.join(sys.path[0], "data", action), "r+t")
    data = fd.read()
    data = bytearray.fromhex(''.join(data))
    print (action)
    device.send_data(data)

def send (action1, action2, delay):
    # step 1
    for action in action1:
        send_single(action)
    # pause
    print("pause " + str(delay) + "s")
    if (delay == 0):
        print("No delay")
        return
    time.sleep(delay)
    # step 2
    for action in action2:
        send_single(action)


#sleep 30 seconds to wait for the board/network initialization end
time.sleep(30)

device = setup("rm4.device")

print("Scheduler start")

schedule.every().day.at("08:15").do(send, ["fenetre.up", "porte.up"], ["porte.stop"], 5)

schedule.every().day.at("12:00").do(send_single, "porte.up")
schedule.every().day.at("12:40").do(send, ["fenetre.down"], ["fenetre.stop"], 9)
schedule.every().day.at("18:00").do(send_single, "fenetre.up")

schedule.every().day.at("21:45").do(send, ["fenetre.down", "porte.down"], ["fenetre.stop", "porte.stop"], 17)

while True:
    schedule.run_pending()
    time.sleep(5)
