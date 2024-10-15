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

import asyncio
import datetime
import logging
import time
from contextlib import suppress

import gunicorn
import httpx
from fastapi import FastAPI, Response
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.responses import PlainTextResponse


logging.basicConfig(level=logging.INFO)
gunicorn.SERVER_SOFTWARE = ''

app = FastAPI()
log = logging.getLogger('m2m-exporter')


class Settings(BaseSettings):
    prometheus: str = 'localhost:9090'
    port: int = 8080
    current_label: str = 'time'
    now_label: str = 'curr'
    loop_interval: int = 300
    skip_metrics: str = ''

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


settings = Settings()
STORED_METRICS: list[str] = []
SKIP_QUERY = ''

if settings.skip_metrics:
    SKIP_QUERY = '|'.join(settings.skip_metrics.split(','))
    SKIP_QUERY = f',__name__!~"{SKIP_QUERY}"'
SKIP_LABELS = ['job', 'endpoint', 'instance', 'pod', 'prometheus', 'service']

API_URL = f'http://{settings.prometheus}/api/v1/query_range'
log.info(f'Using {API_URL=}')
client = httpx.AsyncClient()


@app.get('/metrics', response_class=PlainTextResponse)
async def read_metrics(response: Response):
    response.headers['server'] = ''
    return '\n'.join(STORED_METRICS)


def metric_to_string(name, value, labels=None) -> str:
    if labels:
        labels = '{' + ','.join([f'{k}="{v}"' for k, v in labels.items()]) + '}'
    else:
        labels = ''
    return f'{name}{labels} {value}'


async def get_metrics_for_time(dt: datetime.datetime, time_label: str) -> list[str]:
    query = f'{{{settings.current_label}="{settings.now_label}"{SKIP_QUERY}}}'
    log.info(f'Query: {query} {dt.strftime("%s")=} => {dt=}')
    response = await client.post(
        API_URL,
        data={
            'query': query,
            'start': dt.strftime('%s'),
            'end': dt.strftime('%s'),
            'max_source_resolution': 'auto',  # important for compacted
            'partial_response': 'false',
            'step': 60,
        },
    )
    if response.status_code != 200:
        log.error(f'Error getting metrics: {response.text}')
        return []
    raw_data = response.json()
    # log.info(f'Got {raw_data}')
    data = raw_data.get('data', {}).get('result', [])
    # log.info(f'Got {len(data)} metrics for {time_label}')
    # log.info(f'{data}')
    metrics = []
    for metric in data:
        # log.info(f'{metric=}')
        name = metric['metric'].pop('__name__')
        labels = metric['metric']
        for k in SKIP_LABELS:
            labels.pop(k, None)
        labels[settings.current_label] = time_label
        value = metric['values'][-1][1]
        metrics.append(metric_to_string(name, value, labels))
    log.info(f'Got {metrics=}')
    return metrics


async def update_metrics():
    log.info('update metrics')
    t = time.time()
    new_metrics = []
    new_metrics.extend(await get_metrics_for_time(minus_months(1), 'prev'))
    new_metrics.extend(await get_metrics_for_time(minus_months(2), 'prev_prev'))
    new_metrics.extend(
        [
            metric_to_string('up', 1),
            metric_to_string('last_update', datetime.datetime.now().strftime('%s')),
            metric_to_string('update_duration', f'{time.time() - t:.6f}'),
        ]
    )
    STORED_METRICS[:] = new_metrics


async def update_metrics_loop():
    shutdown = asyncio.Event()
    app.add_event_handler('shutdown', shutdown.set)
    while not shutdown.is_set():
        try:
            await update_metrics()
        except Exception as e:
            log.exception(f'During update: {e}')
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(shutdown.wait(), timeout=settings.loop_interval)


async def spawn_update_metrics_loop():
    asyncio.create_task(update_metrics_loop())


def minus_months(months=1, now=None):
    """
    respects month
    """
    now = now or datetime.datetime.now()
    if now.month <= months:
        return now.replace(year=now.year - 1, month=now.month + 12 - months)
    return now.replace(month=now.month - months)


app.add_event_handler('startup', spawn_update_metrics_loop)


async def async_main():
    await client.__aenter__()
    await update_metrics()


if __name__ == '__main__':
    asyncio.run(async_main())
