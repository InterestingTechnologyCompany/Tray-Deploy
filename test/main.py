import os
import serial
# uv add pyserial. NOT serial, pyserial
import time
import struct
import threading
from flask import Flask, render_template, jsonify, request

PORT = os.getenv('ARDUINO_PORT', '/dev/ttyACM0')
BAUDRATE = 9600

CMD_READ                = 0x01
CMD_WRITE               = 0x02
CMD_REPORT              = 0x03

TARGET_AIR_TEMP         = 0x10
TARGET_AIR_HUMIDITY     = 0x11
TARGET_SOIL_HUMIDITY    = 0x12
TARGET_PUMP             = 0x20
TARGET_LAMP             = 0x21

HEADER                  = 0xFF   
UNIT_ID                 = 0x01

PACKET_FMT = '<BBBBHB' 
PACKET_SIZE = struct.calcsize(PACKET_FMT)

app = Flask(__name__)
ser = None
serial_lock = threading.Lock()

sensor_data = {
    'air_temp': 0.0,
    'air_humidity': 0.0,
    'soil_humidity': 0.0
}

def calculate_checksum(header, unit_id, cmd, target, value):
    val_low = value & 0xFF
    val_high = (value >> 8) & 0xFF
    total = header + unit_id + cmd + target + val_low + val_high
    return total & 0xFF

def send_packet(cmd, target, value=0):
    global ser
    if ser is None or not ser.is_open: return

    with serial_lock: # 쓰기 충돌 방지
        checksum = calculate_checksum(HEADER, UNIT_ID, cmd, target, value)
        packet_data = struct.pack(PACKET_FMT, HEADER, UNIT_ID, cmd, target, value, checksum)
        ser.write(packet_data)
        print(f"[Tx] Cmd:{cmd} Target:{target:02x} Val:{value}")

def serial_listener():
    global ser, sensor_data
    print(">>> Serial Listener Started")
    
    while True:
        if ser is None or not ser.is_open:
            time.sleep(1)
            continue
        
        try:
            if ser.in_waiting >= PACKET_SIZE:
                raw_data = ser.read(PACKET_SIZE)
                
                try:
                    header, unit_id, cmd, target, value, recv_checksum = struct.unpack(PACKET_FMT, raw_data)
                except struct.error:
                    continue

                if header != HEADER:
                    continue

                calc_sum = calculate_checksum(header, unit_id, cmd, target, value)
                if recv_checksum != calc_sum:
                    print(f"[Error] Checksum mismatch! Recv:{recv_checksum}, Calc:{calc_sum}")
                    continue

                if cmd == CMD_REPORT:
                    if target == TARGET_AIR_TEMP:
                        sensor_data['air_temp'] = value / 100.0
                    elif target == TARGET_AIR_HUMIDITY:
                        sensor_data['air_humidity'] = value / 100.0
                    elif target == TARGET_SOIL_HUMIDITY:
                        sensor_data['soil_humidity'] = value / 100.0
            else:
                time.sleep(0.01)

        except Exception as e:
            print(f"Listener Error: {e}")
            time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    return jsonify(sensor_data)

@app.route('/control', methods=['POST'])
def control_device():
    req = request.json
    target = int(req.get('target'))
    value = int(req.get('value'))
    
    send_packet(CMD_WRITE, target, value)
    return jsonify({"status": "sent", "target": target, "value": value})







if __name__ == "__main__":
    try:
        # 시리얼 연결 시도
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        print(f"Connected to {PORT}")
        
        # 아두이노 리셋 대기 (중요)
        time.sleep(3) 
        ser.reset_input_buffer()
        print("Ready...")

        # 리스너 스레드 시작
        t = threading.Thread(target=serial_listener, daemon=True)
        t.start()

        # 플라스크 서버 시작
        app.run(host='0.0.0.0', port=5000, debug=False)

    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        if ser and ser.is_open:
            ser.close()