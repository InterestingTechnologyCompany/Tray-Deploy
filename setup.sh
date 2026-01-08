# TODO: 내부 서버에 필요한 것들만 집어넣어서 거기서 다운받게 만들기. 
# 지금은 파이가 인터넷 연결되어 있다고 가정.
#!/bin/bash

set -e
sudo apt-get update && sudo apt-get install -y --no-install-recommends \
    gcc


# ** 데비안 계열이라 https://docs.docker.com/engine/install/debian/#install-using-the-repository  이 필ㅛ
# install docker
sudo apt-get install -y ca-certificates curl 
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/raspbian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/raspbian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y

sudo apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

rm -rf /var/lib/apt/lists/*

sudo docker run -d \
  --name my-app \
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