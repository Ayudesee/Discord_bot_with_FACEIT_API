import json

from PIL import Image, ImageFont, ImageDraw
import requests
import aiohttp
import asyncio
from ImageCollectors.ProjectExceptions import NothingException
from api_funcs.async_faceit_get_funcs import player_details, player_history, match_stats, region_stats
from decouple import config
# from env_variables import faceit_headers


class ImageCollectorCompare:
    def __init__(
            self, nickname1: str,
            nickname2: str,
            amount: str = "50",
            output_type: str = "games"):
        self.nickname1 = nickname1
        self.nickname2 = nickname2
        self.output_type = self.validate_output_type(output_type)
        self.amount = self.validate_amount(amount)
        self.background = Image.new(mode="RGBA", size=(960, 540))
        self.background = Image.open(f"templates/maps/black.jpg")
        self.draw_bg = ImageDraw.Draw(self.background)
        self.font = ImageFont.truetype(f"templates/fonts/Outfit/Outfit-Bold.ttf", 26)
        self.font_name = ImageFont.truetype(f"templates/fonts/Outfit/Outfit-Bold.ttf", 36)
        self.available_maps = ["de_ancient", "de_dust2", "de_inferno", "de_mirage",
                               "de_nuke", "de_overpass", "de_train", "de_vertigo"]

    @staticmethod
    def validate_output_type(output_type):
        if output_type in ["game", "games", "month", "months", "week", "weeks", "days", "day"]:
            return output_type
        else:
            return "games"

    def validate_amount(self, amount):
        if self.output_type in ["game", "games"]:
            return int(amount) if amount.isdigit() and 5 <= int(amount) <= 100 else 20

    async def collect_image(self):
        async with aiohttp.ClientSession(headers=json.loads(config('faceit_headers'))) as session:
            task1 = asyncio.create_task(self.collect_stat(session, self.nickname1))
            task2 = asyncio.create_task(self.collect_stat(session, self.nickname2))

            player1_stats = await task1
            player2_stats = await task2

            if player1_stats and player2_stats:
                return self.draw_image(player1_stats, player2_stats)

    async def collect_stat(self, session, nickname):
        list_of_games = []
        try:
            pd, history, player_info = await self.get_player_info(session, nickname)
        except NothingException:
            return None

        for match_h in history['items']:
            task = asyncio.create_task(match_stats(session, match_h['match_id']))
            match_stat = await task
            if match_stat is None:
                continue
            for map_s in match_stat['rounds'][::-1]:
                game = self.compile_game(player_info, pd, map_s, match_h)
                list_of_games.append(game)
        return list_of_games

    async def get_player_info(self, session, nickname):
        pd = await player_details(session, nickname)
        # TODO: if output_type is not "games" -> change player_history() call
        if pd is not None:
            history = await player_history(session, pd['player_id'], offset=0, limit=self.amount)
            if history is not None:
                task1 = asyncio.create_task(region_stats(session=session,
                                                         player_id=pd['player_id'],
                                                         region=pd['games']['csgo']['region']))
                task2 = asyncio.create_task(region_stats(session=session,
                                                         player_id=pd['player_id'],
                                                         region=pd['games']['csgo']['region'],
                                                         country=pd['country']))
                region_place = await task1
                country_place = await task2
                region_place = region_place['items'][0]['position']
                country_place = country_place['items'][0]['position']
                player_info = {"nickname": nickname,
                               "region_place": region_place,
                               "country_place": country_place}
                return pd, history, player_info
        raise NothingException

    @staticmethod
    def compile_game(player_info, pd, map_s, match_h):
        game = {}
        for team in map_s['teams']:
            for player in team['players']:
                if pd['player_id'] == player['player_id']:
                    game = {"nickname": player_info['nickname'],
                            "steam_id": pd['games']['csgo']['game_player_id'],
                            "avatar": pd['avatar'],
                            "background": pd['cover_image'],
                            "country": pd['country'],
                            "country_place": player_info['country_place'],
                            "region_place": player_info['region_place'],
                            "player_id": pd['player_id'],
                            "region": pd['games']['csgo']['region'],
                            "skill_level": pd['games']['csgo']['skill_level'],
                            "faceit_elo": pd['games']['csgo']['faceit_elo'],
                            "result": player['player_stats']['Result'],
                            "kills": player['player_stats']['Kills'],
                            "assists": player['player_stats']['Assists'],
                            "deaths": player['player_stats']['Deaths'],
                            "kdratio": player['player_stats']['K/D Ratio'],
                            "krratio": player['player_stats']['K/R Ratio'],
                            "mvps": player['player_stats']['MVPs'],
                            "headshots%": player['player_stats']['Headshots %'],
                            "4k": player['player_stats']['Quadro Kills'],
                            "5k": player['player_stats']['Penta Kills'],
                            "mapscore": map_s['round_stats']['Score'],
                            "mapname": map_s['round_stats']['Map'],
                            "started_at": match_h['started_at']}
        return game

    def get_comparison_dict(self, player1_stats, player2_stats):
        comparison_dict = {"nickname": (player1_stats[0]['nickname'],
                                        player2_stats[0]['nickname']),
                           "steam_id": (player1_stats[0]['steam_id'],
                                        player2_stats[0]['steam_id']),
                           "avatar": (player1_stats[0]['avatar'],
                                      player2_stats[0]['avatar']),
                           "background": (player1_stats[0]['background'],
                                          player2_stats[0]['background']),
                           "country": (player1_stats[0]['country'],
                                       player2_stats[0]['country']),
                           "country_place": (player1_stats[0]['country_place'],
                                             player2_stats[0]['country_place']),
                           "region_place": (player1_stats[0]['region_place'],
                                            player2_stats[0]['region_place']),
                           "player_id": (player1_stats[0]['player_id'],
                                         player2_stats[0]['player_id']),
                           "region": (player1_stats[0]['region'],
                                      player2_stats[0]['region']),
                           "skill_level": (player1_stats[0]['skill_level'],
                                           player2_stats[0]['skill_level']),
                           "faceit_elo": (player1_stats[0]['faceit_elo'],
                                          player2_stats[0]['faceit_elo'])}
        p1_mean_stats = self.get_mean_stats(player1_stats)
        p2_mean_stats = self.get_mean_stats(player2_stats)

        for keys in zip(p1_mean_stats, p2_mean_stats):
            comparison_dict[keys[0]] = (p1_mean_stats[keys[0]], p2_mean_stats[keys[1]])
        return comparison_dict

    def get_mean_stats(self, player_stat):
        mean_k = mean_a = mean_d = mean_kd = mean_kr = mean_hs = total_4k = total_5k = winrate = mvps = 0
        map_dict = {}
        for single_map in self.available_maps:
            map_dict[single_map] = [0, 0]  # [total_played, win_amount]

        for i in range(min(int(self.amount), len(player_stat))):
            mean_k += int(player_stat[i]['kills'])
            mean_a += int(player_stat[i]['assists'])
            mean_d += int(player_stat[i]['deaths'])
            mean_kd += float(player_stat[i]['kdratio'])
            mean_kr += float(player_stat[i]['krratio'])
            mean_hs += float(player_stat[i]['headshots%'])
            total_4k += int(player_stat[i]['4k'])
            total_5k += int(player_stat[i]['5k'])
            winrate += float(player_stat[i]['result'])
            mvps += int(player_stat[i]['mvps'])
            if player_stat[i]['mapname'] in self.available_maps:
                map_dict[player_stat[i]['mapname']][0] += 1
                if player_stat[i]['result'] == "1":
                    map_dict[player_stat[i]['mapname']][1] += 1

        mean_k, mean_a, mean_d, mean_kd, mean_kr, mean_hs, winrate, mvps = \
            map((lambda x: x / len(player_stat)), [mean_k, mean_a, mean_d, mean_kd, mean_kr, mean_hs, winrate, mvps])
        stat_dict = {"mean_k": mean_k, "mean_a": mean_a, "mean_d": mean_d, "mean_kd": mean_kd,
                     "mean_kr": mean_kr, "mean_hs": mean_hs, "winrate": int(winrate * 100),
                     "total_4k": total_4k, "total_5k": total_5k, "mvps": mvps}
        return {**stat_dict, **map_dict}

    @staticmethod
    def get_avatar(avatar):
        if avatar != "":
            avatar_req = requests.get(avatar, stream=True)
            image_avatar = Image.open(avatar_req.raw)
            image_avatar = image_avatar.resize((130, 130))
        else:
            image_avatar = Image.open(f"templates/question-mark-icon.jpg")
            image_avatar = image_avatar.resize((130, 130))
        return image_avatar

    @staticmethod
    def compare_stats(value: tuple, category: str) -> list:
        white = (255, 255, 255, 255)
        green = (0, 190, 0, 255)
        red = (170, 0, 0, 255)

        values_dict = {"1f": {0: {"1.4": [green, red], "1.2": [green, white], "1": [white, white]},
                              1: {"1.4": [red, green], "1.2": [white, green], "1": [white, white]}},
                       "2f": {0: {"1.4": [green, red], "1.2": [green, white], "1": [white, white]},
                              1: {"1.4": [red, green], "1.2": [white, green], "1": [white, white]}},
                       "%": {0: {"1.4": [green, red], "1.2": [green, white], "1": [white, white]},
                             1: {"1.4": [red, green], "1.2": [white, green], "1": [white, white]}},
                       "reverse": {0: {"1.4": [red, green], "1.2": [green, white], "1": [white, white]},
                                   1: {"1.4": [green, red], "1.2": [white, green], "1": [white, white]}},
                       "total": {0: {"1.4": [white, white], "1.2": [white, white], "1": [white, white]},
                                 1: {"1.4": [white, white], "1.2": [white, white], "1": [white, white]}}}

        if not isinstance(value, tuple) or len(value) != 2:
            return [white, white]
        if value[0] == value[1] == 0:
            return values_dict[category][value.index(max(value))]["1"]
        rating = (max(value) / min(value)) if min(value) != 0 else 100
        if rating >= 1.4:
            rating_s = "1.4"
        elif rating >= 1.2:
            rating_s = "1.2"
        else:
            rating_s = "1"
        return values_dict[category][value.index(max(value))][rating_s]

    def place_stat_map(self, comparison_dict):
        map_w, map_h = 90, 50
        map_y_start = 140
        left_stat_x = 110
        right_stat_x = 850
        i = 0
        for key in self.available_maps:
            if comparison_dict[key][0][1] != 0:
                left_line = f"{comparison_dict[key][0][1]} / {comparison_dict[key][0][0]} — " \
                            f"{int(comparison_dict[key][0][1] / comparison_dict[key][0][0] * 100)}%"
            else:
                left_line = f"{comparison_dict[key][0][1]} / {comparison_dict[key][0][0]} — 0%"
            if comparison_dict[key][1][1] != 0:
                right_line = f"{int(comparison_dict[key][1][1] / comparison_dict[key][1][0] * 100)}% — " \
                             f"{comparison_dict[key][1][1]} / {comparison_dict[key][1][0]}"
            else:
                right_line = f"0% — {comparison_dict[key][1][1]} / {comparison_dict[key][1][0]}"

            self.draw_bg.text((left_stat_x, map_h * i + map_y_start + 10), left_line, font=self.font)
            w, h = self.draw_bg.textsize(right_line, font=self.font)
            self.draw_bg.text((right_stat_x - w, map_h * i + map_y_start + 10), right_line, font=self.font)

            current_map = Image.open(f"templates/maps/{key}.jpg")
            current_map = current_map.resize((map_w, map_h))
            self.background.paste(current_map, (10, map_h * i + map_y_start))
            self.background.paste(current_map, (860, map_h * i + map_y_start))
            i += 1

    def draw_stat(self, left_line, right_line, color_left, color_right, idx):
        left_stat_x = 410
        right_stat_x = 550
        start_y = 220
        step = 30
        w, h = self.draw_bg.textsize(left_line, font=self.font)
        self.draw_bg.text((left_stat_x - w, start_y + step * idx), left_line, font=self.font, fill=color_left)
        self.draw_bg.text((right_stat_x, start_y + step * idx), right_line, font=self.font, fill=color_right)

    def place_stat(self, comparison_dict):
        stat_percent = ["mean_hs", "winrate"]
        stat_1f = ["mvps", "mean_k"]
        reverse = ["mean_d"]
        stat_2f = ["mean_kd", "mean_kr"]
        stat_total = ["total_4k", "total_5k", "faceit_elo"]
        i = 0
        self.place_stat_map(comparison_dict)
        for key, value in comparison_dict.items():
            if key in stat_percent:
                color_left, color_right = self.compare_stats(value, "%")
                left_line = f"{int(comparison_dict[key][0])}%"
                right_line = f"{int(comparison_dict[key][1])}%"
                self.draw_stat(left_line, right_line, color_left, color_right, i)
                i += 1
            elif key in stat_1f:
                color_left, color_right = self.compare_stats(value, "1f")
                left_line = f"{comparison_dict[key][0]:.1f}"
                right_line = f"{comparison_dict[key][1]:.1f}"
                self.draw_stat(left_line, right_line, color_left, color_right, i)
                i += 1
            elif key in stat_2f:
                color_left, color_right = self.compare_stats(value, "2f")
                left_line = f"{comparison_dict[key][0]:.2f}"
                right_line = f"{comparison_dict[key][1]:.2f}"
                self.draw_stat(left_line, right_line, color_left, color_right, i)
                i += 1
            elif key in stat_total:
                color_left, color_right = self.compare_stats(value, "total")
                left_line = f"{comparison_dict[key][0]}"
                right_line = f"{comparison_dict[key][1]}"
                self.draw_stat(left_line, right_line, color_left, color_right, i)
                i += 1
            elif key in reverse:
                color_left, color_right = self.compare_stats(value, "reverse")
                left_line = f"{comparison_dict[key][0]:.1f}"
                right_line = f"{comparison_dict[key][1]:.1f}"
                self.draw_stat(left_line, right_line, color_left, color_right, i)
                i += 1

    @staticmethod
    def get_player_background(bg_link, output_width=960, output_height=540):
        if bg_link != "":
            bg_req = requests.get(bg_link, stream=True)
            background = Image.open(bg_req.raw)
        else:
            background = Image.open(f"templates/background_features/dark-right-side-for-stat.png")

        width, height = background.size
        if height != output_height:
            aspect_ratio = output_height / height
            background = background.resize((int(width * aspect_ratio), output_height))
        width, height = background.size
        if width >= output_width:
            left = int((width - output_width) / 2)
            top = 0
            right = int((width - output_width) / 2 + output_width)
            bottom = height
            background = background.crop((left, top, right, bottom))
            background.resize((output_width, output_height))
        return background

    def place_mid_text(self):
        w, h = self.draw_bg.textsize(f"ELO", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 220), f"ELO", font=self.font)
        w, h = self.draw_bg.textsize("avgK", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 250), "avgK", font=self.font)
        w, h = self.draw_bg.textsize("avgD", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 280), "avgD", font=self.font)
        w, h = self.draw_bg.textsize("K/D", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 310), "K/D", font=self.font)
        w, h = self.draw_bg.textsize("K/R", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 340), "K/R", font=self.font)
        w, h = self.draw_bg.textsize("HS", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 370), "HS", font=self.font)
        w, h = self.draw_bg.textsize(f"W/L", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 400), f"W/L", font=self.font)
        w, h = self.draw_bg.textsize("4K", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 430), "4K", font=self.font)
        w, h = self.draw_bg.textsize("5K", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 460), "5K", font=self.font)
        w, h = self.draw_bg.textsize(f"MVP", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 490), f"MVP", font=self.font)

    def draw_image(self, player1_stats, player2_stats):
        dark_bg = Image.open(f"templates/background_features/dark-right-side-for-stat.png")
        dark_middle = Image.open(f"templates/background_features/dark-middle-compare.png")
        player1_bg = self.get_player_background(player1_stats[0]['background'], 480, 540)
        player2_bg = self.get_player_background(player2_stats[0]['background'], 480, 540)
        self.background.paste(player1_bg, (0, 0))
        self.background.paste(player2_bg, (480, 0))
        self.background.paste(dark_bg, (0, 0), dark_bg)
        self.background.paste(dark_middle, (0, 0), dark_middle)
        avatar1 = self.get_avatar(player1_stats[0]['avatar'])
        avatar2 = self.get_avatar(player2_stats[0]['avatar'])
        self.background.paste(avatar1, (10, 10))
        self.background.paste(avatar2, (820, 10))
        self.draw_bg = ImageDraw.Draw(self.background)

        self.draw_bg.text((160, 20), player1_stats[0]['nickname'], font=self.font_name)
        w, h = self.draw_bg.textsize(player2_stats[0]['nickname'], font=self.font_name)
        self.draw_bg.text((810 - w, 20), player2_stats[0]['nickname'], font=self.font_name)

        comparison_dict = self.get_comparison_dict(player1_stats, player2_stats)

        w, h = self.draw_bg.textsize(f"{self.amount} {self.output_type}", font=self.font)
        self.draw_bg.text(((960 - w) / 2, 100), f"{self.amount} {self.output_type}", font=self.font)

        self.place_mid_text()

        self.draw_bg.text((160, 70), f"{comparison_dict['region'][0]}: {comparison_dict['region_place'][0]}",
                          font=self.font)
        self.draw_bg.text((160, 100), f"{comparison_dict['country'][0]}: {comparison_dict['country_place'][0]}",
                          font=self.font)

        self.place_stat(comparison_dict)

        w, h = self.draw_bg.textsize(f"{comparison_dict['region'][1]}: {comparison_dict['region_place'][1]}",
                                     font=self.font)
        self.draw_bg.text((810 - w, 70), f"{comparison_dict['region'][1]}: {comparison_dict['region_place'][1]}",
                          font=self.font)
        w, h = self.draw_bg.textsize(f"{comparison_dict['country'][1]}: {comparison_dict['country_place'][1]}",
                                     font=self.font)
        self.draw_bg.text((810 - w, 100), f"{comparison_dict['country'][1]}: {comparison_dict['country_place'][1]}",
                          font=self.font)

        return self.background
