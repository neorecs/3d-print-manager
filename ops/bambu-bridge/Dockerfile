FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "paho-mqtt>=2,<3" \
    && useradd --create-home bridge
USER bridge
WORKDIR /home/bridge
COPY bridge.py .
CMD ["python", "-u", "bridge.py"]
