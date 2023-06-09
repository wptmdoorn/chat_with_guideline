FROM zauberzeug/nicegui:latest

LABEL maintainer="William van Doorn <wptmdoorn@gmail.com>"

WORKDIR /app
ADD . /app

RUN pip install -r requirements.txt

CMD python3 chatwithguideline/main.py