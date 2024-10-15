PHONY := build
TAG ?= latest
PORT ?= 8081
GHCR_NAME := ghcr.io/cybergrind/m2m-exporter:$(TAG)
LOCAL_NAME=m2m-exporter
LOCAL_IP=$(shell ip -4 addr show docker0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
LOCAL_PROMETHEUS=$(LOCAL_IP):9090


build:
	docker build -f Dockerfile -t m2m-exporter .
	docker tag m2m-exporter $(GHCR_NAME)

docker-run:
	docker rm -f $(LOCAL_NAME) || true
	docker run --name $(LOCAL_NAME) \
		-e NOW_LABEL=now -e PROMETHEUS=$(LOCAL_PROMETHEUS) -e PORT=$(PORT) \
		-e LOOP_INTERVAL=10 \
		-p $(PORT):$(PORT) $(GHCR_NAME)

push:
	docker push $(GHCR_NAME)

server:
	uv run gunicorn -b 0.0.0.0:$(PORT) "src.main:app" \
		--worker-class uvicorn.workers.UvicornWorker
