FROM python:3.12-alpine

WORKDIR /app
COPY . .

RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev libmagic bash \
        && rm -rf .github LICENSE README.MD \
        && pip install --upgrade pip \
        && pip install --no-cache-dir -r requirements.txt \
        && chmod +x entrypoint.sh


CMD ["./entrypoint.sh"]