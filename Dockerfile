FROM python:3

WORKDIR /usr/src/app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . .

ENV UV_PROJECT_ENVIRONMENT=/usr/local

RUN uv sync --locked

ENTRYPOINT ["python", "src/main.py"]
