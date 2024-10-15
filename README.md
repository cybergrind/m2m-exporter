# m2m-exporter

Exporter that makes month to month metrics easy.

When you need to have month-to-month comparisons in prometheus it requires
quite complex logic to handle 31, 30, 29 and 28 days months.

This exportes find all metrics with label `{time="curr"}` and exports them from
1 and 2 months ago with the label `{time="prev"}` and `{time="prev_prev"}`.


### Configuration
You can configure it with the following environment variables:

```
PROMETHEUS=prometheus:9090  # link to prometheus query api
PORT=8080  # local port to listen
# search for {time="curr"}
CURRENT_LABEL=time
NOW_LABEL=now
LOOP_INTERVAL=300
# if you want to skip some metrics
SKIP_METRICS=''
```


Kube configuration example:
```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: m2m-exporter
  labels:
    app: m2m-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: m2m-exporter
  revisionHistoryLimit: 1
  template:
    metadata:
      labels:
        app: m2m-exporter
    spec:
      containers:
        - name: m2m-exporter
          image: ghcr.io/cybergrind/m2m-exporter:latest
          imagePullPolicy: Always
          env:
            - name: PROMETHEUS
              value: prometheus:9090
          readinessProbe:
            httpGet:
              path: /metrics
              port: http
            initialDelaySeconds: 1
            periodSeconds: 5
          ports:
            - name: http
              containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: m2m-exporter
  labels:
    svc: m2m-exporter
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
  selector:
    app: m2m-exporter
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: m2m-exporter
  labels:
    prometheus: enabled
spec:
  selector:
    matchLabels:
      svc: m2m-exporter
  endpoints:
    - port: http
      path: /metrics
      interval: 60s
```
