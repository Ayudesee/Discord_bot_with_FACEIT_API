from fastapi import FastAPI
from decouple import config

from producer import RabbitProducer


app = FastAPI()
rabbit = RabbitProducer(
    config("RMQ_HOST"),
    config("RMQ_PORT"),
)


@app.get("/")
def read_root():
    return {}


@app.post("/match_status_ready")
def respond_status_ready(request: dict):
    print("/match_status_ready called")
    rabbit.send_message("match_status_ready", request)
    return {}


@app.post("/match_status_finished")
def respond_status_finished(request: dict):
    print("/match_status_finished called")
    rabbit.send_message("match_status_finished", request)
    return {}


@app.post("/match_status_aborted")
def respond_status_aborted(request: dict):
    print("/match_status_aborted called")
    rabbit.send_message("match_status_aborted", request)
    return {}
