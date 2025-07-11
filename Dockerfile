ARG VERSION=0.0.4
ARG PORT=25500
ARG API_URL

FROM python:3.13 AS builder

RUN mkdir -p /app/.web
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

ARG VERSION

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY rxconfig.py ./
RUN reflex init

COPY *.web/bun.lockb *.web/package.json .web/
RUN if [ -f .web/bun.lockb ]; then cd .web && ~/.local/share/reflex/bun/bin/bun install --frozen-lockfile; fi

COPY . .

ARG PORT API_URL

RUN REFLEX_API_URL=${API_URL:-http://localhost:$PORT} reflex export --loglevel debug --frontend-only --no-zip && mv .web/build/client/* /srv/ && rm -rf .web



FROM python:3.13-slim


RUN apt-get update -y && apt-get install -y caddy mc && rm -rf /var/lib/apt/lists/*

ARG VERSION
ARG PORT API_URL
ENV PATH="/app/.venv/bin:$PATH" 
ENV PORT=$PORT
ENV REFLEX_API_URL=${API_URL:-http://localhost:$PORT} 
ENV PYTHONUNBUFFERED=1
ENV VERSION=${VERSION}

WORKDIR /app
COPY --from=builder /app /app
COPY --from=builder /srv /srv

STOPSIGNAL SIGKILL

EXPOSE $PORT

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]