FROM python:3.13

WORKDIR /home/code
RUN curl --proto '=https' --tlsv1.2 -LsSf https://github.com/astral-sh/uv/releases/download/0.4.20/uv-installer.sh | sh && cp /root/.cargo/bin/uv /usr/bin/uv
ADD pyproject.toml uv.lock /home/code/
RUN uv sync

COPY src /home/code/src
COPY Makefile /home/code/


ENV PROMETHEUS=prometheus:9090
ENV PORT=8080
ENV CURRENT_LABEL=time
ENV NOW_LABEL=curr
ENV SKIP_METRICS=

CMD make server
