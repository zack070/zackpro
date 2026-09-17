FROM python:3.13-slim-bookworm

# Pre-install everything the verifier needs; test.sh must never apt-get,
# curl or pip install at verify time. pulp is needed to independently
# re-solve the disruption-conditioned Stage B optimum against each
# candidate's own actual end-of-period-4 state (see
# test_procurement_grading.py) -- it must match environment/Dockerfile's
# pinned version exactly.
RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2 pulp==2.9.0

RUN useradd -m -u 1001 -s /bin/bash runner

# Bake tests into the image; harbor does NOT upload tests/ at verify time
COPY . /tests/

# Pre-create the parent dir of every declared artifact, or harbor's upload
# fails with "Could not find the file /app in container"
RUN mkdir -p /app/outputs /work /logs/verifier \
    && chown runner:runner /work
