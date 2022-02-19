import time

import discord
import os
import re
from io import BytesIO
from ImageCollectorMatchFinished import ImageCollectorMatchFinished
from ImageCollectorStatLast import ImageCollectorStatLast
from ImageCollectorCompare import ImageCollectorCompare
from faceit_get_funcs import match_stats, player_details
from IPython.terminal.pt_inputhooks.asyncio import loop
from discord import Client
from flask import Flask, request, Response
from threading import Thread
from functools import partial

Discord_token = os.environ['Discord_token']
app = Flask(__name__)


@app.route("/", methods=["GET"])
def respond_default_get():
    return Response(status=200)


@app.route("/match_status_ready", methods=["POST"])
def respond_status_ready():
    print(request.json)
    loop.create_task(bot_client.post_faceit_message_ready(channel_id=828940900033626113, request_json=request.json))
    print("respond match_status_ready function called")
    return Response(status=200)


@app.route("/match_status_finished", methods=["POST"])
def respond_status_finished():
    print(request.json)
    loop.create_task(bot_client.post_faceit_message_finished(channel_id=828940900033626113, request_json=request.json))
    print("respond match_status_finished function called")
    return Response(status=200)


@app.route("/match_status_aborted", methods=["POST"])
def respond_status_aborted():
    print(request.json)
    loop.create_task(bot_client.post_faceit_message_aborted(channel_id=828940900033626113, request_json=request.json))
    print("respond match_status_aborted function called")
    return Response(status=200)


class MyDiscordClient(discord.Client):
    sub_players = ["ad42c90b-45a9-49b6-8ab0-9c8662330543",
                   "278790a2-1f08-4350-bd96-427f7dcc8722",
                   "18e2a663-9e20-4db9-8b29-3c3cbdff30ac",
                   "8cbb0b36-4c6b-4ebd-a92b-829234016626",
                   "e1cddcbb-afdc-4e8e-abf2-eea5638f0363",
                   "9da3572e-1960-4ba0-bd3c-d38ef34c1f1c",
                   "b8e5cd07-1b43-4203-9173-465fddcd391f",
                   "4e7d1f6c-9045-4800-8eda-23c892dcd814"]

    async def on_ready(self):
        for guild in self.guilds:
            print(f"Logged on as {self.user}, server: {guild.name}, guild_id:{guild.id}")

    @staticmethod
    def compile_binary_image(image):
        if image is not None:
            with BytesIO() as image_binary:
                image.save(image_binary, "PNG")
                image_binary.seek(0)
                binary_image = discord.File(fp=image_binary, filename="image.png")
                return binary_image

    async def on_message(self, message):
        print(f"New message from {message.author}: {message.content}")
        _content: list = message.content.split()
        if message.author.id != 825393722186924112:
            if message.attachments or message.embeds or (message.content.find("https://") != -1) or (
                    message.content.find("http://") != -1):
                await message.add_reaction("👍")
                await message.add_reaction("👎")
            elif bool(re.search("^[.]stats?$", _content[0])) and len(_content) == 2:
                channel = self.get_channel(id=828940900033626113)
                imgclst = ImageCollectorStatLast(_content[1])
                image = imgclst.collect_image()
                await channel.send(file=self.compile_binary_image(image))
            elif bool(re.search("^[.]compare$", message.content.split(" ")[0])) and len(_content) == 5:
                channel = self.get_channel(id=828940900033626113)
                imgcmpr = ImageCollectorCompare(_content[1], _content[2], _content[3], _content[4])
                image = imgcmpr.collect_image()
                await channel.send(file=self.compile_binary_image(image))

    async def on_raw_reaction_add(self, payload):
        upvotes = 0
        downvotes = 0
        users_upvote = []
        users_downvote = []
        if payload.emoji.name == "👍" or payload.emoji.name == "👎":
            print(payload)
            channel = Client.get_channel(self, payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            print(f"Emoji {payload.emoji} added by:{payload.member}, "
                  f"Message by: {message.author}, Message: {message.content}")

            for reaction in message.reactions:
                if reaction.emoji == "👍":
                    users_upvote = await reaction.users().flatten()
                elif reaction.emoji == "👎":
                    users_downvote = await reaction.users().flatten()
            for user in users_upvote:
                if len(user.roles) > 1:
                    upvotes += 1
            for user in users_downvote:
                if len(user.roles) > 1:
                    downvotes += 1

            print(f"Upvotes/Downvotes = {upvotes}/{downvotes}")
            if upvotes < downvotes - 2:
                await message.delete()
                print(f"*** Message \"{message.content}\" deleted with {upvotes} Upvotes, {downvotes} Downvotes\n")

    async def on_raw_reaction_remove(self, payload):
        upvotes = 0
        downvotes = 0
        users_upvote = []
        users_downvote = []
        if payload.emoji.name == "👍" or payload.emoji.name == "👎":
            print(payload)
            channel = Client.get_channel(self, payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            print(f"Emoji {payload.emoji} removed by:{payload.member}, "
                  f"Message by: {message.author}, Message: {message.content}")

            for reaction in message.reactions:
                if reaction.emoji == "👍":
                    users_upvote = await reaction.users().flatten()
                elif reaction.emoji == "👎":
                    users_downvote = await reaction.users().flatten()
            for user in users_upvote:
                if len(user.roles) > 1:
                    upvotes += 1
            for user in users_downvote:
                if len(user.roles) > 1:
                    downvotes += 1

            print(f"Upvotes/Downvotes = {upvotes}/{downvotes}")
            if upvotes < downvotes - 2:
                await message.delete()
                print(f"*** Message \"{message.content}\" deleted with {upvotes} Upvotes, {downvotes} Downvotes\n")

    async def post_faceit_message_ready(self, channel_id, request_json):
        channel = self.get_channel(id=channel_id)
        my_color = 9936031
        embed_msg = discord.Embed(title="Match Ready", type="rich",
                                  description="[{0}](https://www.faceit.com/en/csgo/room/{1})".format(
                                      request_json['payload']['id'], request_json['payload']['id']),
                                  color=my_color)
        str_nick1 = ""
        str_nick2 = ""
        elo1 = ""
        elo2 = ""
        for idx_team, team in enumerate(request_json['payload']['teams']):
            for player in team['roster']:
                if idx_team == 0:
                    str_nick1 += player['nickname'] + "\n"
                    elo1 += str(player_details(player['nickname'])['games']['csgo']['faceit_elo']) + "\n"
                else:
                    str_nick2 += player['nickname'] + "\n"
                    elo2 += str(player_details(player['nickname'])['games']['csgo']['faceit_elo']) + "\n"

        embed_msg.add_field(name=request_json['payload']['teams'][0]['name'], value=str_nick1, inline=True)
        embed_msg.add_field(name="ELO", value=elo1, inline=True)
        embed_msg.add_field(name="\u200b", value="\u200b")
        embed_msg.add_field(name=request_json['payload']['teams'][1]['name'], value=str_nick2, inline=True)
        embed_msg.add_field(name="ELO", value=elo2, inline=True)
        embed_msg.add_field(name="\u200b", value="\u200b")
        await channel.send(embed=embed_msg)

    def get_strnick_embed_color(self, statistics):
        black, green, red, gray = 1, 2067276, 10038562, 9936031
        my_color = black
        is_found_in_first_team = False  # flag for situations where 2 of sub_players are in both teams
        str_nick = ""
        for idx_team, team in enumerate(statistics['rounds'][0]['teams']):
            if idx_team == 1:
                str_nick += "\n"
            for player in team['players']:
                str_nick += f"{player['nickname']}, "
                if player['player_id'] in self.sub_players:
                    if idx_team == 0:
                        is_found_in_first_team = True
                    my_color = green if team['team_stats']['Team Win'] == "1" else red
                    if idx_team == 1 and is_found_in_first_team:
                        my_color = gray
                        break
        str_nick = str_nick[:-2]  # last two symbols are ", "
        return str_nick, my_color

    async def post_faceit_message_finished(self, channel_id, request_json):
        channel = self.get_channel(id=channel_id)

        # loop to wait FaceIt API for 1 minute if we hadn't got response
        statistics = None
        for _ in range(12):
            statistics = match_stats(request_json['payload']['id'])
            if statistics:
                break
            time.sleep(5)

        str_nick, my_color = self.get_strnick_embed_color(statistics)
        embed_msg = discord.Embed(title=str_nick, type="rich",
                                  description="[{0}](https://www.faceit.com/en/csgo/room/{1})".format(
                                      statistics['rounds'][0]['round_stats']['Map'], request_json['payload']['id']),
                                  color=my_color)
        nick1, elo1, nick2, elo2 = await self.delete_message_by_faceit_match_id(match_id=request_json['payload']['id'])

        img_collector = ImageCollectorMatchFinished(request_json, statistics, nick1, elo1, nick2, elo2)
        image_list = img_collector.collect_image()
        for image in image_list:
            embed_msg.set_image(url="attachment://image.png")
            await channel.send(embed=embed_msg, file=self.compile_binary_image(image))

    async def post_faceit_message_aborted(self, channel_id, request_json):
        await self.delete_message_by_faceit_match_id(channel_id, request_json['payload']['id'])

    async def delete_message_by_faceit_match_id(self, channel_id=828940900033626113, match_id=None):
        channel = Client.get_channel(self, channel_id)
        messages = await channel.history(limit=10).flatten()
        nick1, elo1, nick2, elo2 = "", "", "", ""
        for message in messages:
            if message.embeds and match_id in message.embeds[0].description:
                nick1 = message.embeds[0].fields[0].value
                elo1 = message.embeds[0].fields[1].value
                nick2 = message.embeds[0].fields[3].value
                elo2 = message.embeds[0].fields[4].value
                await message.delete()
        return nick1, elo1, nick2, elo2


if __name__ == "__main__":
    intents = discord.Intents.all()
    bot_client = MyDiscordClient(intents=intents)

    port = int(os.environ.get("PORT", 5000))
    print(f"variable port:{port}")
    partial_run = partial(app.run, host="0.0.0.0", port=port)

    t = Thread(target=partial_run)
    t.start()

    bot_client.run(Discord_token)
