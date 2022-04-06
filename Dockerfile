FROM python:3.10.4-alpine3.15

ENV PYTHONUNBUFFERED=1

ENV HOME=/code
WORKDIR ${HOME}

COPY requirements.txt ./
COPY src/*.py ./

RUN pip install --upgrade pip &&\
    pip install -r requirements.txt
