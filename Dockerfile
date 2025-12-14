FROM docker.io/library/python:3.12-slim as builder
#LABEL "for fun"

ENV NEO4J_URI=bolt://neo4j:7687
ENV NEO4J_USER=neo4juser
ENV NEO4J_PASSWORD=password
ENV NEO4J_DATABASE=neo4j

RUN mkdir -p /opt/kgfx
WORKDIR /opt/kgfx
COPY . .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# for healthcheck
RUN apt-get -y update; apt-get -y install curl
CMD [ "uvicorn","main:app","--host","0.0.0.0","--reload","--port","8001" ]