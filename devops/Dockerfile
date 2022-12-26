ARG VERSION=3.10-slim-bullseye
ARG PIP_DEFAULT_TIMEOUT=100
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ARG PYTHONUNBUFFERED=1
ARG PYTHONDONTWRITEBYTECODE=1

FROM python:$VERSION AS requirements-stage

WORKDIR /tmp

ENV PIP_DEFAULT_TIMEOUT=$PIP_DEFAULT_TIMEOUT \
    PIP_DISABLE_PIP_VERSION_CHECK=$PIP_DISABLE_PIP_VERSION_CHECK \
    PIP_NO_CACHE_DIR=$PIP_NO_CACHE_DIR \
    PYTHONUNBUFFERED=$PYTHONUNBUFFERED \
    PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE

RUN pip install poetry

COPY webapp/poetry.lock webapp/pyproject.toml /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:$VERSION

WORKDIR /opt/app

ENV PIP_DEFAULT_TIMEOUT=$PIP_DEFAULT_TIMEOUT \
    PIP_DISABLE_PIP_VERSION_CHECK=$PIP_DISABLE_PIP_VERSION_CHECK \
    PIP_NO_CACHE_DIR=$PIP_NO_CACHE_DIR \
    PYTHONUNBUFFERED=$PYTHONUNBUFFERED \
    PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE

COPY --from=requirements-stage /tmp/requirements.txt /opt/app/requirements.txt
COPY devops/certs/rootCA.crt /usr/local/share/ca-certificates/

RUN update-ca-certificates
RUN apt-get update -y && apt-get install git gcc g++ -y
RUN pip install -r ./requirements.txt

COPY webapp /opt/app

RUN useradd -g users appuser
RUN chown -R appuser /opt/app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
