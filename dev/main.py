#pip install pyserial
# we well eventually have to rewrite this whole shit in c++ for performance reason
# we will HAVE TO implement GStreamer instead of cv2 eventually

import serial
import time
import struct
import threading
from flask import Flask, render_template_string, jsonify, request

# -------
PORT                    = '####'  # TODO: 니 포트로 변경
BAUDRATE                = 9600
USB_CAM                 = 0
# -------

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

sensor_data = {
    'air_temp' : 0.0,
    'air_humidity' : 0.0,
    'soil_humidity' : 0.0,
    # 'lamp_brightness':0.0,
    # 'fan_speed' : 0.0,
}
serial_lock = threading.Lock() # 쓰기 충돌 방지


app = Flask(__name__)

def calculate_checksum(header, unit_id, cmd, target, value):
    val_low = value & 0xFF
    val_high = (value >> 8) & 0xFF
    total = header + unit_id + cmd + target + val_low + val_high
    return total & 0xFF

def send_packet(cmd, target, value=0):
    """
    웹에서 제어 명령(WRITE)을 보낼 때만 사용
    """
    global ser
    if ser is None or not ser.is_open: return
    
    with serial_lock: # 쓰기 도중 다른 쓰기 방지
        checksum = calculate_checksum(HEADER, UNIT_ID, cmd, target, value)
        packet_data = struct.pack(PACKET_FMT, HEADER, UNIT_ID, cmd, target, value, checksum)
        ser.write(packet_data)
        print(f"[Tx] Cmd:{cmd} Target:{target} Val:{value}")    


def serial_listener():
    
    global ser, sensor_data
    
    while 1:
        if ser is None or not ser.is_open:
            time.sleep(1)
            continue
        
        try:
            if ser.in_waiting >= PACKET_SIZE:
                raw_data = ser.read(PACKET_SIZE)
                
                if raw_data[0] != HEADER:
                    print("Invalid header, skipping byte")
                    ser.read(1)
                    continue
                try:
                    header, unit_id, cmd, target, value, checksum = struct.unpack(PACKET_FMT, raw_data)
                except struct.error:
                    continue
                
                calc_checksum = calculate_checksum(header, unit_id, cmd, target, value)
                if checksum != calc_checksum:
                    print("Checksum mismatch, skipping packet")
                    continue
                
                if cmd == CMD_REPORT:
                    if target == TARGET_AIR_TEMP:
                        sensor_data['air_temp'] = value / 100.0
                    elif target == TARGET_AIR_HUMIDITY:
                        sensor_data['air_humidity'] = value / 100.0
                    elif target == TARGET_SOIL_HUMIDITY:
                        sensor_data['soil_humidity'] = value / 100.0
                    # print(f"[Rx] Cmd:{cmd} Target:{target} Val:{value}")
                    
            else:
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Listener error: {e}")
            time.sleep(1)
            


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Farm Control</title>
    <style>
        body { font-family: 'Arial', sans-serif; text-align: center; background: #f4f4f4; padding: 20px;}
        .container { display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 200px; }
        .card h3 { margin: 0 0 10px; color: #555; }
        .value { font-size: 2.5em; font-weight: bold; color: #2c3e50; }
        .unit { font-size: 0.5em; color: #7f8c8d; }
        button { padding: 15px 30px; font-size: 1.2em; border: none; border-radius: 8px; cursor: pointer; margin: 10px; transition: 0.3s; }
        .btn-on { background-color: #f1c40f; color: #333; }
        .btn-off { background-color: #95a5a6; color: white; }
        button:hover { opacity: 0.8; transform: scale(1.05); }
    </style>
    <script>
        function updateSensors() {
            fetch('/data')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('t_air').innerText = d.air_temp;
                    document.getElementById('h_air').innerText = d.air_humi;
                    document.getElementById('h_soil').innerText = d.soil_humi;
                });
        }
        
        function setLamp(val) {
            fetch('/control/lamp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({value: val})
            });
        }
        setInterval(updateSensors, 500); // 0.5초마다 갱신
    </script>
</head>
<body>
    <h1>🌿 Smart Farm System</h1>
    
    <div class="container">
        <div class="card">
            <h3>Air Temp</h3>
            <div class="value"><span id="t_air">--</span><span class="unit">°C</span></div>
        </div>
        <div class="card">
            <h3>Air Humi</h3>
            <div class="value"><span id="h_air">--</span><span class="unit">%</span></div>
        </div>
        <div class="card">
            <h3>Soil Humi</h3>
            <div class="value"><span id="h_soil">--</span><span class="unit">%</span></div>
        </div>
    </div>

    <div class="card" style="width: auto; display: inline-block;">
        <h3>Lamp Control</h3>
        <button class="btn-on" onclick="setLamp(128)">ON</button>
        <button class="btn-off" onclick="setLamp(0)">OFF</button>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    return jsonify(sensor_data)

@app.route('/control/lamp', methods=['POST'])
def control_lamp():
    req = request.json
    val = int(req.get('value', 0))
    send_packet(CMD_WRITE, TARGET_LAMP, val)
    return jsonify({"status": "sent", "val": val})



## main program

if __name__ == "__main__":
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=0.1) # timeout을 짧게
        time.sleep(2)
        ser.reset_input_buffer()
        print(f"Connected to {PORT}")

        # 리스너 스레드 시작 (데몬 스레드: 메인 종료시 자동 종료)
        t = threading.Thread(target=serial_listener, daemon=True)
        t.start()

        app.run(host='0.0.0.0', port=5000, debug=False) ## True 치면 2개 생기면서 시리얼 꼬일 확률 높음 하지마

    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()