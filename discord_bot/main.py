import asyncio
from functools import partial
import discord
from decouple import config

from discord_bot import MyDiscordClient
from consumer import RabbitConsumer
from threading import Thread
import nest_asyncio
nest_asyncio.apply()


async def main():
    loop = asyncio.get_running_loop()
    print(f"{loop=}")
    intents = discord.Intents.all()
    bot = MyDiscordClient(intents=intents, loop=loop)
    queue_func_map = {
        "match_status_ready": bot.post_faceit_message_ready,
        "match_status_finished": bot.post_faceit_message_finished,
        "match_status_aborted": bot.post_faceit_message_aborted,
    }
    consumer = RabbitConsumer("localhost", 5672, queue_func_map)
    thread1 = Thread(target=consumer.start_consuming)
    thread1.start()
    # consumer.start_consuming()

    print('after consumer.start_consuming()')
    bot.run(config('discord_token'))


if __name__ == '__main__':
    intents = discord.Intents.all()
    bot = MyDiscordClient(intents=intents)
    queue_func_map = {
        "match_status_ready": bot.post_faceit_message_ready,
        "match_status_finished": bot.post_faceit_message_finished,
        "match_status_aborted": bot.post_faceit_message_aborted,
    }
    consumer = RabbitConsumer("localhost", 5672, queue_func_map)
    # thread1 = Thread(target=consumer.start_consuming)
    # thread1.start()
    # consumer.start_consuming()

    t = Thread(target=partial(consumer.start_consuming))
    t.start()
    # asyncio.run(main())

    bot.run(config('discord_token'))
