FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

ARG TARGET_FOLDER=src

# 1. requirements.txt 도 동적으로 해당 폴더에서 가져옵니다.
COPY ${TARGET_FOLDER}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. 소스 코드도 해당 폴더(dev/test/src) 내용을 내부 src 폴더로 복사합니다.
COPY ${TARGET_FOLDER}/ ./src/

COPY LICENSE .

CMD ["python", "src/main.py"]