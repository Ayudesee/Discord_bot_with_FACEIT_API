import pika
import json
import asyncio
import nest_asyncio
from IPython.terminal.pt_inputhooks.asyncio import loop
nest_asyncio.apply()


class RabbitConsumer:
    def __init__(self, host: str = "localhost", port: int = 5672, queue_func_map: dict = None):
        if queue_func_map is None:
            queue_func_map = []
        self.host = host
        self.port = port
        self.queue_func_map = queue_func_map
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port
            )
        )
        self.channel = self.connection.channel()
        self.declare_queues()

    def declare_queues(self):
        for queue, bot_callback in self.queue_func_map.items():
            self.channel.basic_consume(queue, self.on_message)

    def on_message(self, channel, method_frame, header_frame, body):
        print("Message received")
        data = json.loads(body)
        print(data)
        # loop = asyncio.get_running_loop()
        loop.create_task(self.queue_func_map[method_frame.routing_key](
            channel_id=828940900033626113, request_json=data))
        # task = asyncio.create_task(self.queue_func_map[method_frame.routing_key](
        #     channel_id=828940900033626113, request_json=data)
        # )  # вызов функции бота через create task()
        # await self.queue_func_map[method_frame.routing_key](
        #     channel_id=828940900033626113, request_json=data)
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)

    def start_consuming(self):
        try:
            print('Started consuming messages')
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        self.connection.close()
