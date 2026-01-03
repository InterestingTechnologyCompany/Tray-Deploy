# TODO: Rewrite this in C++ if rpi is too slow

import serial
import struct
import time
import sys

#TODO: CHANGE THIS TO ACTUAL SERIAL PORT
SERIAL_PORT = '/dev/'
BAUD_RATE = 9600

CMD_READ   = 0x01
CMD_WRITE  = 0x02
CMD_REPORT = 0x03

TARGETS = {
    'AIR_TEMP': 0x10,
    'AIR_HUMIDITY': 0x11,
    'SOIL_HUMIDITY': 0x12,
    'PUMP': 0x20,
    'LAMP': 0x21
}

TARGET_NAMES = {v: k for k, v in TARGETS.items()}

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f" Connected : {SERIAL_PORT}")
    time.sleep(2) # Arduino reset delay
except Exception as e:
    print(e)
    sys.exit()
    
    
def calculate_checksum(uid, cmd, target, value):
    val_low = value & 0xFF
    val_high = (value >> 8) & 0xFF
    return (uid + cmd + target + val_low + val_high) & 0xFF

def send_packet(unit_id, cmd, target, value):
    header = 0xFF
    checksum = calculate_checksum(unit_id, cmd, target, value)
    
    packet = struct.pack('<BBBBHB', header, unit_id, cmd, target, value, checksum)
    
    ser.write(packet)
    print(f"\n   [SENT] ID:{unit_id} Cmd:{cmd} Tgt:{target} Val:{value}")
    print(f"   Raw: {packet.hex().upper()}")
    


def read_response():
    print("Waiting for response...", end='', flush=True)
    start_time = time.time()
    
    while time.time() - start_time < 2.0:
        if ser.in_waiting >= 7:
            data = ser.read(7)
            
            header, uid, cmd, target, value, chk = struct.unpack('<BBBBHB', data)
            
            if header != 0xFF:
                # wrong header
                # print ("wrong header")
                return
            
            calc_chk = calculate_checksum(uid, cmd, target, value)
            if chk != calc_chk:
                # checksum error
                # print("checksum error")
                return

            print(f"\n [RECV] ID:{uid} Cmd:{cmd} Target:{TARGET_NAMES.get(target, 'Unknown')}")
            
            if target in [TARGETS['AIR_TEMP'], TARGETS['AIR_HUMID']]:
                print(f"   👉 Value: {value / 10.0}")
            else:
                print(f"   👉 Value: {value}")
            return
            
        time.sleep(0.1)
    print("No response (Timeout)")
    
    