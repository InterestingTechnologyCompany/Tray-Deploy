import serial
import time
import struct
import threading
from flask import Flask, render_template_string, jsonify, request

# ==========================================
# 1. 설정 및 상수 (main (1).py 기반)
# ==========================================
PORT = 'COM3'  # TODO: 본인 포트로 꼭 변경하세요 (맥/리눅스는 /dev/tty...)
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

# 패킷 포맷: < (Little Endian), B(1), B(1), B(1), B(1), H(2), B(1)
PACKET_FMT = '<BBBBHB' 
PACKET_SIZE = struct.calcsize(PACKET_FMT)

# ==========================================
# 2. 전역 변수 및 객체
# ==========================================
app = Flask(__name__)
ser = None
serial_lock = threading.Lock() # 시리얼 충돌 방지용

# 웹이랑 공유할 센서 데이터
sensor_data = {
    'air_temp': 0.0,
    'air_humidity': 0.0,
    'soil_humidity': 0.0
}

# ==========================================
# 3. 통신 프로토콜 함수 (main (1).py 로직 유지)
# ==========================================
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

# ==========================================
# 4. 백그라운드 시리얼 리스너 (스레드)
# ==========================================
def serial_listener():
    global ser, sensor_data
    print(">>> Serial Listener Started")
    
    while True:
        if ser is None or not ser.is_open:
            time.sleep(1)
            continue
        
        try:
            if ser.in_waiting >= PACKET_SIZE:
                # 락을 걸지 않고 읽기 (읽기는 블로킹되면 안되므로)
                # 데이터가 깨질 경우를 대비해 1바이트씩 읽는게 안전하지만
                # 일단 작동한다고 하신 main (1).py 방식 그대로 사용합니다.
                raw_data = ser.read(PACKET_SIZE)
                
                try:
                    header, unit_id, cmd, target, value, recv_checksum = struct.unpack(PACKET_FMT, raw_data)
                except struct.error:
                    continue # 패킷 사이즈 안맞으면 무시

                # 헤더 체크
                if header != HEADER:
                    # 싱크가 안 맞으면 한 바이트 뒤로 밀어서 다시 맞추는게 좋지만
                    # 여기서는 단순하게 처리합니다.
                    continue

                # 체크섬 검증
                calc_sum = calculate_checksum(header, unit_id, cmd, target, value)
                if recv_checksum != calc_sum:
                    print(f"[Error] Checksum mismatch! Recv:{recv_checksum}, Calc:{calc_sum}")
                    continue

                # 데이터 파싱 및 저장
                if cmd == CMD_REPORT:
                    # 타겟에 따라 올바른 변수에 저장
                    if target == TARGET_AIR_TEMP:
                        sensor_data['air_temp'] = value / 100.0
                    elif target == TARGET_AIR_HUMIDITY:
                        sensor_data['air_humidity'] = value / 100.0
                    elif target == TARGET_SOIL_HUMIDITY:
                        sensor_data['soil_humidity'] = value / 100.0
                    
                    # 디버깅 출력
                    # print(f"[Rx] Target: {target:x}, Val: {value}")

            else:
                # 데이터 없으면 CPU 과부하 방지용 대기
                time.sleep(0.01)

        except Exception as e:
            print(f"Listener Error: {e}")
            time.sleep(1)

# ==========================================
# 5. 웹 서버 (Flask)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Farm</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: #f0f2f5; margin: 0; padding: 20px; }
        h1 { color: #2c3e50; }
        .dashboard { display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 220px; }
        .card h3 { margin: 0 0 10px; color: #7f8c8d; font-size: 1em; }
        .value { font-size: 2.5em; font-weight: bold; color: #2c3e50; }
        .unit { font-size: 0.5em; color: #95a5a6; }
        
        .controls { background: white; padding: 20px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .control-group { margin: 15px 0; }
        button { padding: 10px 20px; font-size: 1rem; border: none; border-radius: 5px; cursor: pointer; margin: 0 5px; transition: 0.2s; }
        .btn-on { background-color: #2ecc71; color: white; }
        .btn-off { background-color: #e74c3c; color: white; }
        button:hover { opacity: 0.9; transform: scale(1.05); }
    </style>
    <script>
        function updateSensors() {
            fetch('/data')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('t_air').innerText = d.air_temp.toFixed(2);
                    document.getElementById('h_air').innerText = d.air_humidity.toFixed(2);
                    document.getElementById('h_soil').innerText = d.soil_humidity.toFixed(2);
                });
        }
        
        function sendControl(target, val) {
            fetch('/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target: target, value: val})
            });
        }
        
        // 1초마다 센서 데이터 갱신
        setInterval(updateSensors, 1000);
    </script>
</head>
<body>
    <h1>🌿 Smart Farm Monitor</h1>
    
    <div class="dashboard">
        <div class="card">
            <h3>Air Temperature</h3>
            <div class="value"><span id="t_air">--</span><span class="unit">°C</span></div>
        </div>
        <div class="card">
            <h3>Air Humidity</h3>
            <div class="value"><span id="h_air">--</span><span class="unit">%</span></div>
        </div>
        <div class="card">
            <h3>Soil Humidity</h3>
            <div class="value"><span id="h_soil">--</span><span class="unit">%</span></div>
        </div>
    </div>

    <div class="controls">
        <h3>Device Control</h3>
        <div class="control-group">
            <span>💡 LAMP: </span>
            <button class="btn-on" onclick="sendControl(0x21, 128)">ON</button>
            <button class="btn-off" onclick="sendControl(0x21, 0)">OFF</button>
        </div>
        <div class="control-group">
            <span>💧 PUMP: </span>
            <button class="btn-on" onclick="sendControl(0x20, 128)">ON</button>
            <button class="btn-off" onclick="sendControl(0x20, 0)">OFF</button>
        </div>
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

@app.route('/control', methods=['POST'])
def control_device():
    req = request.json
    target = int(req.get('target'))
    value = int(req.get('value'))
    
    # 아두이노로 명령 전송
    send_packet(CMD_WRITE, target, value)
    return jsonify({"status": "sent", "target": target, "value": value})

# ==========================================
# 6. 메인 실행부
# ==========================================
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