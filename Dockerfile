FROM ubuntu:20.04
WORKDIR /app/
COPY requirements.txt /app/
RUN pip install requirements.txt
COPY . /app/
