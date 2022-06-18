import json

from PIL import Image, ImageFont, ImageDraw
import requests
import asyncio
import aiohttp
from api_funcs.async_faceit_get_funcs import player_details
from decouple import config
# from env_variables import faceit_headers


class ImageCollectorMatchFinished:
    def __init__(self, request_json, stat_json, prev_nick1, prev_elo1, prev_nick2, prev_elo2):
        self._fonts = self.get_fonts(font_folder="Outfit", font_file="Outfit-Bold.ttf",
                                     font_file_mainscore="Outfit-ExtraBold.ttf")
        self._elo_change_team1, self._elo_change_team2 = "", ""
        self.request_json = request_json
        self.stat_json = stat_json
        self.prev_nick1 = prev_nick1
        self.prev_nick2 = prev_nick2
        self.prev_elo1 = prev_elo1
        self.prev_elo2 = prev_elo2
        self.stat_color = (255, 255, 255, 255)
        self.image_map = Image.new(mode="RGBA", size=(960, 540))
        self.image_map = Image.open(f"templates/maps/black.jpg")
        self.draw_image_map = ImageDraw.Draw(self.image_map)
        self.image_dark_avatar_bot = Image.open("templates/background_features/for_avatar_bot.png")
        self.image_dark_avatar_top = Image.open("templates/background_features/for_avatar_top.png")
        self.image_dark_middle = Image.open("templates/background_features/dark-middle2.png")
        self.available_maps = ["de_ancient", "de_dust2", "de_inferno", "de_mirage",
                               "de_nuke", "de_overpass", "de_train", "de_vertigo"]

    async def collect_image(self):
        image_list = []
        tasks = []
        for idx_match, match in enumerate(self.stat_json['rounds']):
            self.draw_map_image(match)
            async with aiohttp.ClientSession(headers=json.loads(config('faceit_headers'))) as session:
                for idx_team, team in enumerate(match['teams']):
                    for idx_player, player in enumerate(team['players']):
                        task = asyncio.create_task(
                            self.draw_player_on_image(
                                session,
                                player,
                                idx_team,
                                idx_player))
                        tasks.append(task)
                await asyncio.gather(*tasks)
                image_list.append(self.image_map)
        return image_list

    @staticmethod
    def bool_overtime_check(match):
        if "Overtime score" in match['teams'][0]['team_stats'].keys() and \
                match['teams'][0]['team_stats']['Overtime score'] == "0" and \
                match['teams'][1]['team_stats']['Overtime score'] == "0":
            return False
        else:
            return True

    def calculate_elo_change(self, player, player_elo):
        elo_diff = ""
        nicknames = (self.prev_nick1 + "\n" + self.prev_nick2).split("\n")
        prevelo = (self.prev_elo1 + "\n" + self.prev_elo2).split("\n")
        for idx, nick in enumerate(nicknames):
            if nick == player['nickname']:
                if int(prevelo[idx]) > int(player_elo):
                    elo_diff = "(" + str((int(player_elo) - int(prevelo[idx]))) + ")"
                elif int(prevelo[idx]) < int(player_elo):
                    elo_diff = "(+" + str(int(player_elo) - int(prevelo[idx])) + ")"
                else:
                    break
        return elo_diff

    def draw_map_image(self, match):
        if match['round_stats']['Map'] in self.available_maps:
            self.image_map = Image.open(f"templates/maps/{match['round_stats']['Map']}.jpg")
        self.image_map = self.image_map.resize((960, 540))
        self.draw_image_map = ImageDraw.Draw(self.image_map)
        if match['teams'][0]['team_stats']['Team Win'] == "1":
            image_topcolor = Image.open("templates/background_features/Win-topleft.png")
            image_botcolor = Image.open("templates/background_features/Lose-botleft.png")
        else:
            image_topcolor = Image.open("templates/background_features/Lose-topleft.png")
            image_botcolor = Image.open("templates/background_features/Win-botleft.png")
        self.image_map.paste(image_topcolor, (0, 0), image_topcolor)
        self.image_map.paste(image_botcolor, (0, 0), image_botcolor)
        self.image_map.paste(self.image_dark_middle, (0, 0), self.image_dark_middle)

        w, h = self.draw_image_map.textsize(match["teams"][0]["team_stats"]["Final Score"],
                                            font=self._fonts['mainscore'])
        self.draw_image_map.text(((146 - w) / 2, 65),
                                 match["teams"][0]["team_stats"]["Final Score"],
                                 font=self._fonts['mainscore'])
        w, h = self.draw_image_map.textsize(match["teams"][1]["team_stats"]["Final Score"],
                                            font=self._fonts['mainscore'])
        self.draw_image_map.text(((146 - w) / 2, 415),
                                 match["teams"][1]["team_stats"]["Final Score"],
                                 font=self._fonts['mainscore'])

        is_overtime_in_match = self.bool_overtime_check(match)
        for idx_team, team in enumerate(match['teams']):
            if is_overtime_in_match:
                halftimes = f"{team['team_stats']['First Half Score']}" \
                            f"—{team['team_stats']['Second Half Score']}" \
                            f"—{team['team_stats']['Overtime score']}"
            else:
                halftimes = f"{team['team_stats']['First Half Score']}" \
                            f"—{team['team_stats']['Second Half Score']}"
            w, h = self.draw_image_map.textsize(halftimes, font=self._fonts['halftime'])
            self.draw_image_map.text(((146 - w) / 2, 235 + 42 * idx_team),
                                     halftimes,
                                     font=self._fonts['halftime'])

    @staticmethod
    def get_fonts(font_folder, font_file, font_file_mainscore):
        fonts = {'mainscore': ImageFont.truetype(f"templates/fonts/{font_folder}/{font_file_mainscore}", 50),
                 'avatar': ImageFont.truetype(f"templates/fonts/{font_folder}/{font_file}", 18),
                 'player_score': ImageFont.truetype(f"templates/fonts/{font_folder}/{font_file}", 32),
                 'player_stats': ImageFont.truetype(f"templates/fonts/{font_folder}/{font_file}", 22),
                 'halftime': ImageFont.truetype(f"templates/fonts/{font_folder}/{font_file}", 22)
                 }
        return fonts

    async def draw_player_on_image(self, session, player, idx_team, idx_player):
        await self.draw_avatar_on_image(session, player, idx_team, idx_player)
        self.draw_player_stats_on_image(player, idx_team, idx_player)

    async def draw_avatar_on_image(self, session, player, idx_team, idx_player):
        player_elo = await player_details(session, player['nickname'])
        player_elo = str(player_elo['games']['csgo']['faceit_elo'])
        elo_diff = self.calculate_elo_change(player, player_elo)
        for idx_req_player, req_player in enumerate(
                self.request_json['payload']['teams'][idx_team]['roster']):
            if player['nickname'] == req_player['nickname']:
                if req_player['avatar'] != "":
                    avatar_req = requests.get(req_player['avatar'], stream=True)
                    image_avatar = Image.open(avatar_req.raw)
                    image_avatar = image_avatar.convert('RGB')
                    image_avatar = image_avatar.resize((130, 130))
                else:
                    image_avatar = Image.open("templates/question-mark-icon.jpg")
                    image_avatar = image_avatar.resize((130, 130))
                draw_image_avatar = ImageDraw.Draw(image_avatar)
                faceitlvl = req_player['game_skill_level']

                if idx_team == 0:
                    image_avatar.paste(self.image_dark_avatar_bot,
                                       (0, 0),
                                       self.image_dark_avatar_bot)

                    image_avatar.paste(self.image_dark_avatar_top,
                                       (0, 0),
                                       self.image_dark_avatar_top)

                    image_avatar.paste(
                        Image.open(f"templates/faceit_icons/faceit{faceitlvl}.png").convert("RGBA"),
                        (0, 0),
                        Image.open(f"templates/faceit_icons/faceit{faceitlvl}.png").convert("RGBA"))

                    w, h = self.draw_image_map.textsize(elo_diff, font=self._fonts['avatar'])
                    draw_image_avatar.text((127 - w, 0), elo_diff, font=self._fonts['avatar'])
                    # w, h = self.draw_image_map.textsize(player_elo, font=self._fonts['avatar'])
                    draw_image_avatar.text((26, 0), player_elo, font=self._fonts['avatar'])
                else:
                    image_avatar.paste(self.image_dark_avatar_top,
                                       (0, 0),
                                       self.image_dark_avatar_top)

                    image_avatar.paste(self.image_dark_avatar_bot,
                                       (0, 0),
                                       self.image_dark_avatar_bot)

                    image_avatar.paste(
                        Image.open(f"templates/faceit_icons/faceit{faceitlvl}.png").convert("RGBA"),
                        (0, 106),
                        Image.open(f"templates/faceit_icons/faceit{faceitlvl}.png").convert("RGBA"))

                    w, h = self.draw_image_map.textsize(elo_diff, font=self._fonts['avatar'])
                    draw_image_avatar.text((127 - w, 107), elo_diff, font=self._fonts['avatar'])
                    # w, h = self.draw_image_map.textsize(player_elo, font=self._fonts['avatar'])
                    draw_image_avatar.text((26, 107), player_elo, font=self._fonts['avatar'])

                w, h = self.draw_image_map.textsize(req_player['nickname'], font=self._fonts['avatar'])
                if w > 130:
                    draw_image_avatar.text((0, 107 - idx_team * 107),
                                           req_player['nickname'],
                                           font=self._fonts['avatar'])
                else:
                    draw_image_avatar.text(((130 - w) / 2, 107 - idx_team * 107),
                                           req_player['nickname'],
                                           font=self._fonts['avatar'])

                self.image_map.paste(image_avatar, (146 + idx_player * 162, 20 + 370 * idx_team))

    def draw_player_stats_on_image(self, player, idx_team, idx_player):
        if float(player["player_stats"]["K/D Ratio"]) >= 1.3:
            self.stat_color = (0, 190, 0, 255)
        elif float(player["player_stats"]["K/D Ratio"]) < 0.6:
            self.stat_color = (170, 0, 0, 255)
        elif 0.8 > float(player["player_stats"]["K/D Ratio"]) >= 0.6:
            self.stat_color = (255, 165, 0, 255)
        else:
            self.stat_color = (255, 255, 255, 255)

        kad = f"{player['player_stats']['Kills']}" \
              f"/{player['player_stats']['Assists']}" \
              f"/{player['player_stats']['Deaths']}"
        w, h = self.draw_image_map.textsize(kad, font=self._fonts['player_score'])
        self.draw_image_map.text((130 + (162 - w) / 2 + idx_player * 162, 155 + 195 * idx_team), kad,
                                 font=self._fonts['player_score'])
        mvp = f"MVP: {player['player_stats']['MVPs']}"
        self.draw_image_map.text((156 + idx_player * 162, 240 + 36 * idx_team), mvp, font=self._fonts['player_stats'])
        kr = f"K/R: {player['player_stats']['K/R Ratio']}"
        self.draw_image_map.text((156 + idx_player * 162, 220 + 76 * idx_team), kr, font=self._fonts['player_stats'])
        kd = f"K/D: {player['player_stats']['K/D Ratio']}"
        self.draw_image_map.text((156 + idx_player * 162, 200 + 116 * idx_team), kd, font=self._fonts['player_stats'],
                                 fill=self.stat_color)
