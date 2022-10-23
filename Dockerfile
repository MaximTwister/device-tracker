FROM python:3

WORKDIR /device_tracker
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY device_tracker /

# next DOCKER-COMPOSE
