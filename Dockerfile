FROM python:3.12-alpine AS builder

WORKDIR /app
COPY . .

RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        libffi-dev \
        libmagic \
        bash \
        && pip install --upgrade pip \
        && pip install pyinstaller \
        && pip install --no-cache-dir -r requirements.txt


CMD ["python","main.py"]