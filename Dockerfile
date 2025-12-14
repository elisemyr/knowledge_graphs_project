FROM docker.io/library/python:3.12-slim as builder
#LABEL "for fun"

RUN mkdir -p /opt/kgfx
WORKDIR /opt/kgfx
COPY . .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

#pyenv virtualenv toto
#pyenv activate toto
#RUN pip install pyenv-virtualenv
#RUN python3 -m venv .venv
# RUN source .venv/bin/activate
RUN pip install --upgrade pip
#RUN pip install virtualenv pyenv
#RUN pyenv virtualenv 3.12.8 kgfx
#RUN pyenv activate kgfx
RUN pip install -r requirements.txt
CMD [ "uvicorn","main:app","--reload","--port","8001" ]