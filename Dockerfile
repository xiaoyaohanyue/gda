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
        && pip install --no-cache-dir -r requirements.txt \
        && pyinstaller --onefile main.py

FROM alpine

WORKDIR /app

COPY --from=builder /app/dist/main /app/main
COPY --from=builder /app/config/ /app/config/

# RUN apk add --no-cache libmagic

CMD ["./main"]