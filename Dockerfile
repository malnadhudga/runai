FROM python

WORKDIR /crew

COPY . .

ENV PIP_NO_INPUT=1

RUN python -m venv /venv

RUN /venv/bin/pip install --upgrade pip setuptools wheel \
 && /venv/bin/pip install .

ENV PATH="/venv/bin:$PATH"

ENTRYPOINT ["crew"]
