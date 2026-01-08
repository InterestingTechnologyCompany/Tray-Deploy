# TODO: 내부 서버에 필요한 것들만 집어넣어서 거기서 다운받게 만들기. 
# 지금은 파이가 인터넷 연결되어 있다고 가정.
#!/bin/bash

set -e
sudo apt-get update && sudo apt-get install -y --no-install-recommends \
    gcc

sudo apt update -y
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update -y

sudo docker run -d \
  --name my-app \
  -p 5000:5000 \
  --restart always \
  --privileged \
  -e ARDUINO_PORT=/dev/ttyACM1 \
  donghunc/tray:test

sudo docker run -d \
  --name watchtower \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 30 --cleanup