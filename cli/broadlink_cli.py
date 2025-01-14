#!/usr/bin/env python3
import argparse
import base64
import codecs
import time

# Use the broadlink lib in the subfolder to use the frequency selection feature
import sys 
sys.path.append('..')

import broadlink
from broadlink.const import DEFAULT_PORT
from broadlink.exceptions import ReadError, StorageError

TICK = 32.84
TIMEOUT = 30
IR_TOKEN = 0x26


def auto_int(x):
    return int(x, 0)


def to_microseconds(bytes):
    result = []
    #  print bytes[0] # 0x26 = 38for IR
    index = 4
    while index < len(bytes):
        chunk = bytes[index]
        index += 1
        if chunk == 0:
            chunk = bytes[index]
            chunk = 256 * chunk + bytes[index + 1]
            index += 2
        result.append(int(round(chunk * TICK)))
        if chunk == 0x0d05:
            break
    return result


def durations_to_broadlink(durations):
    result = bytearray()
    result.append(IR_TOKEN)
    result.append(0)
    result.append(len(durations) % 256)
    result.append(len(durations) / 256)
    for dur in durations:
        num = int(round(dur / TICK))
        if num > 255:
            result.append(0)
            result.append(num / 256)
        result.append(num % 256)
    return result


def format_durations(data):
    result = ''
    for i in range(0, len(data)):
        if len(result) > 0:
            result += ' '
        result += ('+' if i % 2 == 0 else '-') + str(data[i])
    return result


def parse_durations(str):
    result = []
    for s in str.split():
        result.append(abs(int(s)))
    return result


parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
parser.add_argument("--device", help="device definition as 'type host mac'")
parser.add_argument("--type", type=auto_int, default=0x2712, help="type of device")
parser.add_argument("--host", help="host address")
parser.add_argument("--mac", help="mac address (hex reverse), as used by python-broadlink library")
parser.add_argument("--temperature", action="store_true", help="request temperature from device")
parser.add_argument("--humidity", action="store_true", help="request humidity from device")
parser.add_argument("--energy", action="store_true", help="request energy consumption from device")
parser.add_argument("--check", action="store_true", help="check current power state")
parser.add_argument("--checknl", action="store_true", help="check current nightlight state")
parser.add_argument("--turnon", action="store_true", help="turn on device")
parser.add_argument("--turnoff", action="store_true", help="turn off device")
parser.add_argument("--turnnlon", action="store_true", help="turn on nightlight on the device")
parser.add_argument("--turnnloff", action="store_true", help="turn off nightlight on the device")
parser.add_argument("--switch", action="store_true", help="switch state from on to off and off to on")
parser.add_argument("--send", action="store_true", help="send command")
parser.add_argument("--sensors", action="store_true", help="check all sensors")
parser.add_argument("--learn", action="store_true", help="learn command")
parser.add_argument("--rflearn", action="store_true", help="rf scan learning")
parser.add_argument("--frequency", type=float, help="specify radiofrequency for learning")
parser.add_argument("--learnfile", help="save learned command to a specified file")
parser.add_argument("--durations", action="store_true",
                    help="use durations in micro seconds instead of the Broadlink format")
parser.add_argument("--convert", action="store_true", help="convert input data to durations")
parser.add_argument("--joinwifi", nargs=2, help="Args are SSID PASSPHRASE to configure Broadlink device with")
parser.add_argument("data", nargs='*', help="Data to send or convert")
args = parser.parse_args()

if args.device:
    values = args.device.split()
    devtype = int(values[0], 0)
    host = values[1]
    mac = bytearray.fromhex(values[2])
elif args.mac:
    devtype = args.type
    host = args.host
    mac = bytearray.fromhex(args.mac)

if args.host or args.device:
    dev = broadlink.gendevice(devtype, (host, DEFAULT_PORT), mac)
    dev.auth()

if args.joinwifi:
    broadlink.setup(args.joinwifi[0], args.joinwifi[1], 4)

if args.convert:
    data = bytearray.fromhex(''.join(args.data))
    durations = to_microseconds(data)
    print(format_durations(durations))
if args.temperature:
    print(dev.check_temperature())
if args.humidity:
    print(dev.check_humidity())
if args.energy:
    print(dev.get_energy())
if args.sensors:
    data = dev.check_sensors()
    for key in data:
        print("{} {}".format(key, data[key]))
if args.send:
    data = durations_to_broadlink(parse_durations(' '.join(args.data))) \
        if args.durations else bytearray.fromhex(''.join(args.data))
    dev.send_data(data)
if args.learn or (args.learnfile and not args.rflearn):
    dev.enter_learning()
    print("Learning...")
    start = time.time()
    while time.time() - start < TIMEOUT:
        time.sleep(1)
        try:
            data = dev.check_data()
        except (ReadError, StorageError):
            continue
        else:
            break
    else:
        print("No data received...")
        exit(1)

    learned = format_durations(to_microseconds(bytearray(data))) \
        if args.durations \
        else ''.join(format(x, '02x') for x in bytearray(data))
    if args.learn:
        print(learned)
        decode_hex = codecs.getdecoder("hex_codec")
        print("Base64: " + str(base64.b64encode(decode_hex(learned)[0])))
    if args.learnfile:
        print("Saving to {}".format(args.learnfile))
        with open(args.learnfile, "w") as text_file:
            text_file.write(learned)
if args.check:
    if dev.check_power():
        print('* ON *')
    else:
        print('* OFF *')
if args.checknl:
    if dev.check_nightlight():
        print('* ON *')
    else:
        print('* OFF *')
if args.turnon:
    dev.set_power(True)
    if dev.check_power():
        print('== Turned * ON * ==')
    else:
        print('!! Still OFF !!')
if args.turnoff:
    dev.set_power(False)
    if dev.check_power():
        print('!! Still ON !!')
    else:
        print('== Turned * OFF * ==')
if args.turnnlon:
    dev.set_nightlight(True)
    if dev.check_nightlight():
        print('== Turned * ON * ==')
    else:
        print('!! Still OFF !!')
if args.turnnloff:
    dev.set_nightlight(False)
    if dev.check_nightlight():
        print('!! Still ON !!')
    else:
        print('== Turned * OFF * ==')
if args.switch:
    if dev.check_power():
        dev.set_power(False)
        print('* Switch to OFF *')
    else:
        dev.set_power(True)
        print('* Switch to ON *')
if args.rflearn:
    if args.frequency:
        frequency = args.frequency
        print("Press the button you want to learn, a short press...")
    else:
        dev.sweep_frequency()
        print("Detecting radiofrequency, press and hold the button to learn...")

        start = time.time()
        while time.time() - start < TIMEOUT:
            time.sleep(1)
            locked, frequency = dev.check_frequency()
            if locked:
                break
        else:
            print("Radiofrequency not found")
            dev.cancel_sweep_frequency()
            exit(1)

        print("Radiofrequency detected: {}MHz".format(frequency))
        print("You can now let go of the button")

        input("Press enter to continue...")

        print("Press the button again, now a short press.")

    dev.find_rf_packet(frequency)

    start = time.time()
    while time.time() - start < TIMEOUT:
        time.sleep(1)
        try:
            data = dev.check_data()
        except (ReadError, StorageError):
            continue
        else:
            break
    else:
        print("No data received...")
        exit(1)

    print("Packet found!")
    learned = format_durations(to_microseconds(bytearray(data))) \
        if args.durations \
        else ''.join(format(x, '02x') for x in bytearray(data))
    learned = format_durations(to_microseconds(bytearray(data))) \
        if args.durations \
        else ''.join(format(x, '02x') for x in bytearray(data))
    if args.learnfile is None:
        print(learned)
        decode_hex = codecs.getdecoder("hex_codec")
        print("Base64: {}".format(str(base64.b64encode(decode_hex(learned)[0]))))
    if args.learnfile is not None:
        print("Saving to {}".format(args.learnfile))
        with open(args.learnfile, "w") as text_file:
            text_file.write(learned)
