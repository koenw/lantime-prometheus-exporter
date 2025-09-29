FROM python:3

WORKDIR /usr/src/app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . .

RUN uv sync --locked

ENTRYPOINT ["uv", "run", "python", "src/main.py"]
