FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir pulp==2.9.0

WORKDIR /app
COPY . /app

RUN mkdir -p /app/outputs
