
FROM python:3.8-slim-buster AS builder

ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /code

COPY ./requirements.txt .


RUN python -m venv venv

ENV PATH="/code/venv/bin:$PATH"

RUN pip install -r requirements.txt

## multi stage build
FROM python:3.8-slim-buster


WORKDIR /code
ENV PYTHONUNBUFFERED 1

COPY --from=builder /code/venv /code/venv

COPY .env.dev .env

COPY . .

RUN chmod +x web-entrypoint.sh

RUN chmod +x celery-entrypoint.sh

