PHONY := build
TAG ?= latest
PORT ?= 8081
GHCR_NAME := ghcr.io/cybergrind/m2m-exporter:$(TAG)
LOCAL_NAME=m2m-exporter
LOCAL_IP=$(shell ip -4 addr show docker0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
LOCAL_PROMETHEUS=$(LOCAL_IP):9090


build:
	docker build -f Dockerfile -t m2m-exporter .


docker-run:
	docker rm -f $(LOCAL_NAME) || true
	docker run --name $(LOCAL_NAME) -e PROMETHEUS=$(LOCAL_PROMETHEUS) m2m-exporter:latest

push:
	docker tag m2m-exporter $(GHCR_NAME)
	docker push $(GHCR_NAME)

server:
	uv run gunicorn -b localhost:$(PORT) "src.main:app" \
		--worker-class uvicorn.workers.UvicornWorker
