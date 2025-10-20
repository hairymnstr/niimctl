#!/usr/bin/env python3

"""
NAME
    niimctl - CLI tool for printing labels on a NiimBot B1

SYNOPSIS
    niimctl [OPTIONS]

DESCRIPTION
    -h, --help
        Show this help and exit
    -p, --port=DEVICE
        [required] the port the printer is attached to
        e.g. /dev/ttyACM0
    -v, --verbose
        Print debugging info
    -i, --image=FILENAME
        [required] Image to print
"""

import serial
import sys
import getopt
import struct
import time
from PIL import Image

verbose = False
def debug_print(msg):
    global verbose
    if verbose:
        print(msg)

def send_packet(port, cmd, payload):
    packet = bytes([0x55, 0x55])
    packet += bytes([cmd, len(payload)])
    packet += payload

    cks = 0
    for b in packet[2:]:
        cks ^= b
    packet += bytes([cks, 0xaa, 0xaa])

    debug_print(packet)

    port.write(packet)

def recv_packet(port):
    port.timeout = 1.0

    state = "idle"
    while True:
        c = port.read()
        if c == b"":
            debug_print("Timeout")
            return None
        if state == "idle":
            if c == b"\x55":
                state = "started"
            else:
                debug_print(f"Unexpected character, not start: {c}")
        elif state == "started":
            if c == b"\x55":
                state = "cmd"
            else:
                debug_print(f"Unexpected character for second start: {c}")
                state = "idle"
        elif state == "cmd":
            cmd = c[0]
            state = "payload_len"
        elif state == "payload_len":
            payload_len = c[0]
            payload = b""
            state = "payload"
        elif state == "payload":
            payload += c
            if len(payload) == payload_len:
                state = "checksum"
        elif state == "checksum":
            cks = cmd ^ payload_len
            for x in payload:
                cks ^= x
            if cks != c[0]:
                debug_print(f"Checksum mismatch, got {c[0]} calculated {cks}")
                return None
            state = "end"
        elif state == "end":
            if c != b"\xaa":
                debug_print(f"Tail byte one not AA: {c}")
                return None
            state = "end2"
        elif state == "end2":
            if c != b"\xaa":
                debug_print(f"Tail byte two not AA: {c}")
                return None
            break

    return (cmd, payload)

def error_exit(msg, code):
    print(msg)
    print("Try 'niimctl --help' for more information")
    sys.exit(code)

try:
    opts, args = getopt.getopt(sys.argv[1:], "hp:vi:", ("help", "port=", "verbose", "image="))
except getopt.GetoptError as err:
    error_exit(str(err), -1)

portname = None
imagename = None

for o, a in opts:
    if o in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    elif o in ("-p", "--port"):
        portname = a
    elif o in ("-v", "--verbose"):
        verbose = True
    elif o in ("-i", "--image"):
        imagename = a

if portname == None:
    error_exit("You must provide the port that the printer is connected to", -1)

if imagename == None:
    error_exit("You must provide the image name to load and print", -1)

im = Image.open(imagename)
if not im.size == (400,240):
    error_exit("Image must be 400x240 pixels", -1)

im.convert("1")
xim = im.load()

rows = []

for y in range(240):
    rows.append([0] * 50)
    for x in range(400):
        if xim[x, y][0] == 0:
            rows[y][x // 8] = rows[y][x // 8] | (1 << (7 - (x % 8)))

s = serial.Serial(portname)

# set density
# send a single byte 1 2 3 4 or 5 to default 3 code 0x21
send_packet(s, 0x21, b"\x03")
# receive single byte 1 = ok, 0 = error code 0x31
print(recv_packet(s))

# set label type
# unknown 3 label types 1 2 or 3 according to some code? code 0x23
send_packet(s, 0x23, b"\x01")
print(recv_packet(s))

# print start
# 7 byte variant needed for B1 printer
# 2 byte page count (total page types x number of each type)
# 4 bytes unknown 0
# 1 byte page colour unknown 0
send_packet(s, 0x01, struct.pack(">HIB", 1, 0, 0))
print(recv_packet(s))

# repeat page
pages = [1]
for page in pages:
    # page start
    debug_print("Page start")
    send_packet(s, 0x03, b"\x01")
    print(recv_packet(s))

    # set page size
    # 13 byte variant, row, col, copies, unknown 0, unknown 0, unknown 0, unknown 0
    debug_print("Set page size")
    send_packet(s, 0x13, struct.pack(">HHH", 240, 400, 1))
    print(recv_packet(s))

    # print row (repeat)
    blank_rows = 0
    blank_start = -1
    for row_num, row in enumerate(rows):
        if sum(row) == 0:
            if blank_rows == 0:
                blank_start = row_num
            blank_rows += 1
        else:
            if blank_rows:
                send_packet(s, 0x84, struct.pack(">HB", blank_start, blank_rows))
                blank_rows = 0
            printpx = 0
            for b in row:
                for x in range(8):
                    if b & (1 << x):
                        printpx += 1
            payload = struct.pack(">HHH", row_num, printpx, 1)
            payload += bytes(row)
            send_packet(s, 0x85, payload)

    if blank_rows:
        send_packet(s, 0x84, struct.pack(">HB", blank_start, blank_rows))

    # for row in range(60):
    #     # send 2 blank lines
    #     send_packet(s, 0x84, struct.pack(">HB", row * 4, 2))
    #     # print(recv_packet(s))

    #     # send 2 grid pattern lines
    #     payload = b""
    #     payload += struct.pack(">H", row * 4 + 2) # row number
    #     payload += struct.pack(">H", 100)         # number of black pixels in line
    #     payload += struct.pack(">H", 2)           # repeat row 2 times
    #     payload += b"\x81" * 50         # 48 * 8 = 384 pixels
    #     send_packet(s, 0x85, payload)
    #     # print(recv_packet(s))

    # page end
    # don't send page end until you've got these two mysterious packets
    p = recv_packet(s)
    debug_print(p)    
    p = recv_packet(s)
    debug_print(p)
    send_packet(s, 0xe3, b"\x01")
    p = recv_packet(s)
    debug_print(p)

# poll print status
for x in range(100):
    send_packet(s, 0xa3, b"")

    p = recv_packet(s)
    print(p)
    print(struct.unpack(">HHHHH", p[1]))

    time.sleep(0.2)

# print end
send_packet(s, 0xf3, b"\x01")