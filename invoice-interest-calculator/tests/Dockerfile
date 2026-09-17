FROM python:3.13-slim

RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2

RUN useradd -m -u 1001 -s /bin/bash runner

COPY . /tests
WORKDIR /tests

ENTRYPOINT ["bash", "/tests/test.sh"]
