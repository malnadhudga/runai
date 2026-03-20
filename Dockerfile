FROM python:3.12-slim

WORKDIR /crew

ENV PIP_NO_INPUT=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m venv /venv

COPY requirements.txt pyproject.toml ./
RUN /venv/bin/pip install --upgrade pip setuptools wheel \
 && /venv/bin/pip install -r requirements.txt

COPY . .
RUN /venv/bin/pip install --no-deps .

ENV PATH="/venv/bin:$PATH"

ENTRYPOINT ["crew"]
