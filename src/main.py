#!/usr/bin/env python3
"""
env:
  PROMETHEUS - host, required
  PORT - default 8080
  CURRENT_LABEL = 'time' - label for current metrics
  NOW_LABEL = 'now' - current metril label value

Uses /api/v1/query_range to get all all metrics with:
    {CURRENT_LABEL="NOW_LABEL"}
The searches metrics backwards for 1 and 2 months and exposes
previous values
"""
import os
import datetime
from fastapi import FastAPI
import httpx
import logging
import asyncio


logging.basicConfig(level=logging.INFO)

app = FastAPI()
log = logging.getLogger('m2m-exporter')
STORED_METRICS: list[str] = []

SKIP_METRICS = os.getenv('SKIP_METRICS', 'revenue')
SKIP_QUERY = ''
if SKIP_METRICS:
    SKIP_QUERY = '|'.join(SKIP_METRICS.split(','))
    SKIP_QUERY = f',__name__!~"{SKIP_QUERY}"'
PROMETHEUS = os.getenv('PROMETHEUS', 'localhost:9090')
PORT = os.getenv('PORT', 8080)
CURRENT_LABEL = os.getenv('CURRENT_LABEL', 'time')
NOW_LABEL = os.getenv('NOW_LABEL', 'now')
LOOP_INTERVAL = 60

API_URL = f'http://{PROMETHEUS}/api/v1/query_range'
client = httpx.AsyncClient()

@app.get("/metrics")
async def read_metrics():
    return '\n'.join(STORED_METRICS)


def metric_to_string(name, value, labels={}) -> str:
    if labels:
        labels = '{' + ','.join([f'{k}="{v}"' for k, v in labels.items()]) + '}'
    return f'{name}{labels} {value}'

SKIP_LABELS = ['job', 'endpoint', 'instance', 'pod', 'prometheus', 'service']
async def get_metrics_for_time(dt: datetime.datetime, time_label: str) -> list[str]:
    query = f'{{{CURRENT_LABEL}="{NOW_LABEL}"{SKIP_QUERY}}} @ end()'
    #query = 'up'
    log.info(f'Query: {query} {dt.strftime("%s")=} => {dt=}')
    response = await client.post(API_URL, data={
        'query': query,
        'start': (dt-datetime.timedelta(seconds=600)).strftime('%s'),
        'end': dt.strftime('%s'),
        'max_source_resolution': 'auto',  # important for compacted
        'partial_response': 'false',
        'step': 60
    })
    if response.status_code != 200:
        log.error(f'Error getting metrics: {response.text}')
        return []
    raw_data = response.json()
    #log.info(f'Got {raw_data}')
    data = raw_data.get('data', {}).get('result', [])
    #log.info(f'Got {len(data)} metrics for {time_label}')
    #log.info(f'{data}')
    metrics = []
    for metric in data:
        #log.info(f'{metric=}')
        name = metric['metric'].pop('__name__')
        labels = metric['metric']
        for k in SKIP_LABELS:
            labels.pop(k, None)
        labels[CURRENT_LABEL] = time_label
        value = metric['values'][-1][1]
        metrics.append(metric_to_string(name, value, labels))
    log.info(f'Got {metrics=}')
    return metrics



async def update_metrics():
    log.info('update metrics')
    new_metrics = []
    new_metrics.extend(await get_metrics_for_time(minus_months(1), 'prev'))
    new_metrics.extend(await get_metrics_for_time(minus_months(2), 'prev_prev'))
    STORED_METRICS[:] = new_metrics


async def update_metrics_loop():
    shutdown = asyncio.Event()
    app.add_event_handler("shutdown", shutdown.set)
    while not shutdown.is_set():
        await update_metrics()
        await asyncio.sleep(LOOP_INTERVAL)


def minus_months(months=1, now=None):
    """
    respects month
    """
    now = now or datetime.datetime.now()
    if now.month <= months:
        return now.replace(year=now.year-1, month=now.month+12-months)
    return now.replace(month=now.month-months)

app.add_event_handler("startup", update_metrics_loop)

async def async_main():
    await client.__aenter__()
    await update_metrics()


if __name__ == '__main__':
    asyncio.run(async_main())
