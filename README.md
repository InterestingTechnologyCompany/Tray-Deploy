# Tray Operating Docker Image

### Docker Images

- [tray](hub.docker.com/donghunc/tray) - Main image for Tray Operating System deployment

### License

This project is licensed under the terms of the **AGPL-3.0 License**.



### Image distribution

* test : `docker pull donghunc/tray:test`
* main : `docker pull donghunc/tray:latest`
* dev : `docker pull donghunc/tray:dev`

test는 main에  용도로 사용. 작동은 할거임
dev는 개발용으로 사용. 테스트 전 단계. 작동하는지 안하는지 모름
main은 작동하는 지금 운영 버전


하는일들 

main :
- 주요 기능:
    1. 환경 데이터(공기 온도/습도, 토양 습도) 실시간 모니터링 및 수신
    2. 하드웨어 장치(펌프, 램프 등) 제어 명령 전송
    3. 체크섬(Checksum) 검증을 통한 데이터 무결성 체크
"""

dev :
- 주요 기능:
    1. 멀티스레딩(Threading): 백그라운드에서 실시간으로 시리얼 데이터를 수신(Listener).
    2. 데이터 시각화: 웹 대시보드를 통해 온도, 습도, 토양 습도 수치를 실시간 출력.
    3. 원격 제어: 웹 버튼 클릭 시 시리얼 패킷을 생성하여 조명(Lamp) 등 장치 제어.
    4. 동기화: Threading.Lock을 사용하여 시리얼 포트 데이터 쓰기 충돌 방지.


test : 
    지금은 뭐 없음