FROM python:3.12-slim

RUN mkdir /app
WORKDIR /app/
RUN apt-get update && apt-get install -y curl
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false
# RUN poetry install --no-interaction --no-ansi
COPY . .