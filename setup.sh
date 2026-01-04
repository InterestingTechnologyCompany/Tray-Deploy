# TODO: 내부 서버에 필요한 것들만 집어넣어서 거기서 다운받게 만들기. 
##      지금 이 코드 아마 실행하면 버그 날 것 같음 라즈베리파이가 인터넷에 연결된게 아니면

apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

docker run -d --name my-app --restart always donghunc/tray:latest

docker run -d \
  --name watchtower \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 30 --cleanup