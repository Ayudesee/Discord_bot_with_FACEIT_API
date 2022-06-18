import pika
import json


class RabbitProducer:
    def __init__(self, host: str = "localhost", port: int = 5672, queues: list = None, exchange: str = "matches"):
        if queues is None:
            queues = []
        self.host = host
        self.port = port
        self.exchange = exchange
        self.queues = queues
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port
            )
        )
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange="matches")
        self.declare_queues()

    def declare_queues(self):
        for queue in self.queues:
            self.channel.queue_declare(queue=queue)
            self.channel.queue_bind(queue, self.exchange, queue)

    def send_message(self, queue: str, message: dict):
        self.channel.basic_publish(
            exchange='matches',
            routing_key=queue,
            body=json.dumps(message, indent=2).encode('utf-8')
        )
        print(f'Sent {message}')

    # def __del__(self):
    #     self.connection.close()
