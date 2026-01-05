#pip install pyserial
# we well eventually have to rewrite this whole shit in c++ for performance reason
# we will HAVE TO implement GStreamer eventually

import cv2
import serial
import time
import struct
import random

CMD_READ    = 0x01
CMD_WRITE   = 0x02
CMD_REPORT  = 0x03

TARGET_AIR_TEMP       = 0x10
TARGET_AIR_HUMIDITY   = 0x11
TARGET_SOIL_HUMIDITY  = 0x12
TARGET_PUMP           = 0x20
TARGET_LAMP           = 0x21

HEADER = 0xFF   
UNIT_ID = 0x01


PORT = '/dev/ttyUSB0'  # TODO: 니 포트로 변경

# LE
# B: unsigned char (1byte), H: unsigned short (2bytes)
# header(B), unitID(B), cmd(B), target(B), value(H), checksum(B)
PACKET_FMT = '<BBBBHB' 
PACKET_SIZE = struct.calcsize(PACKET_FMT)

def calculate_checksum(header, unit_id, cmd, target, value):
    val_low = value & 0xFF
    val_high = (value >> 8) & 0xFF
    total = header + unit_id + cmd + target + val_low + val_high
    return total & 0xFF

def send_packet(ser, cmd, target, value=0):
    checksum = calculate_checksum(HEADER, UNIT_ID, cmd, target, value)
    
    packet_data = struct.pack(PACKET_FMT, HEADER, UNIT_ID, cmd, target, value, checksum)
    
    ser.write(packet_data)

def read_packet(ser):
    if ser.in_waiting >= PACKET_SIZE:
        raw_data = ser.read(PACKET_SIZE)
        
        try:
            header, unit_id, cmd, target, value, recv_checksum = struct.unpack(PACKET_FMT, raw_data)
        except struct.error:
            print("Error: Packet structure mismatch")
            return None

        calc_checksum = calculate_checksum(header, unit_id, cmd, target, value)
        
        if recv_checksum != calc_checksum:
            print(f"E Checksum mismatch! Recv: {recv_checksum:#02x}, Calc: {calc_checksum:#02x}")
            return None
            
        return {
            "header": header,
            "unitID": unit_id,
            "cmd": cmd,
            "target": target,
            "value": value
        }
    return None

def main():
    BAUDRATE = 9600

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        print(f"Connected to {PORT}")
        
        time.sleep(5) 
        ser.reset_input_buffer() 
        print("Ready via Serial")

        while True:
            
            time.sleep(0.5)
            send_packet(ser, CMD_READ, TARGET_AIR_HUMIDITY)
            time.sleep(0.1) # 아두이노 처리 대기
            
            resp = read_packet(ser)
            if resp and resp['cmd'] == CMD_REPORT:
                humid_val = resp['value'] / 100.0
                print(f"[Rx] Air Humidity: {humid_val:.2f}% (Raw: {resp['value']})")
            
            time.sleep(0.5)
            send_packet(ser, CMD_READ, TARGET_AIR_TEMP)
            time.sleep(0.1) # 아두이노 처리 대기
            
            resp = read_packet(ser)
            if resp and resp['cmd'] == CMD_REPORT:
                temp_val = resp['value'] / 100.0
                print(f"[Rx] Air Temp: {temp_val:.2f}°C (Raw: {resp['value']})")

            time.sleep(0.5)
            send_packet(ser, CMD_READ, TARGET_SOIL_HUMIDITY)
            time.sleep(0.1)
            
            resp = read_packet(ser)
            if resp and resp['cmd'] == CMD_REPORT:
                humi_val = resp['value'] / 100.0
                print(f"[Rx] Soil Humi: {humi_val:.2f}% (Raw: {resp['value']})")
                
            
            send_packet(ser, CMD_WRITE, TARGET_LAMP, 128)

            print("-" * 30)
            time.sleep(2) # 2초 간격 반복

    except serial.SerialException as e:
        print(f"Serial E: {e}")
    except KeyboardInterrupt:
        print("\nExiting program")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()