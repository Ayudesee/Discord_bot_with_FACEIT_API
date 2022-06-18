import asyncio
import json

import aiohttp
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime
import requests
import calendar
from api_funcs.async_faceit_get_funcs import player_details, region_stats, player_history, match_stats
from api_funcs.async_steam_funcs import user_app_stat, user_rec_played_stat
# from env_variables import faceit_headers
from decouple import config


class ImageCollectorStatLast:
    def __init__(self, nickname):
        self.nickname = nickname

    async def collect_image(self):
        task = asyncio.create_task(self.collect_stat(self.nickname))
        player_stat = await task
        if player_stat:
            image = await self.draw_image(player_stat)
            return image
        else:
            return None

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

    @staticmethod
    async def get_player_info(session, nickname):
        pd = await player_details(session, nickname)
        if pd is not None:
            history = await player_history(session, pd['player_id'])
            if history is not None:
                region_place = await region_stats(session=session, player_id=pd['player_id'],
                                                  region=pd['games']['csgo']['region'])
                region_place = region_place['items'][0]['position']
                country_place = await region_stats(session=session, player_id=pd['player_id'],
                                                   region=pd['games']['csgo']['region'],
                                                   country=pd['country'])
                country_place = country_place['items'][0]['position']
                player_info = {"nickname": nickname,
                               "region_place": region_place,
                               "country_place": country_place}
                return pd, history, player_info
        raise ValueError

    async def collect_stat(self, nickname):
        list_of_games = []
        async with aiohttp.ClientSession(headers=json.loads(config('faceit_headers'))) as session:
            try:
                task1 = asyncio.create_task(self.get_player_info(session, nickname))
                pd, history, player_info = await task1
            except ValueError:
                return None

            for match_h in history['items']:
                task2 = asyncio.create_task(match_stats(session, match_h['match_id']))
                match_stat = await task2
                if match_stat is None:
                    continue
                for map_s in match_stat['rounds'][::-1]:
                    game = self.compile_game(player_info, pd, map_s, match_h)
                    list_of_games.append(game)

                    if len(list_of_games) >= 10:
                        return list_of_games
        return list_of_games

    @staticmethod
    async def draw_image(player_stat):
        font = ImageFont.truetype(f"templates/fonts/Outfit/Outfit-Bold.ttf", 26)
        font_name = ImageFont.truetype(f"templates/fonts/Outfit/Outfit-Bold.ttf", 36)
        if player_stat[0]['background'] != "":
            bg_req = requests.get(player_stat[0]['background'], stream=True)
            image_background = Image.open(bg_req.raw)
        else:
            image_background = Image.open(f"templates/background_features/dark-right-side-for-stat.png")

        lose_bg = Image.open(f"templates/background_features/right-side-lose.png")
        win_bg = Image.open(f"templates/background_features/right-side-win.png")

        width, height = image_background.size
        if height != 540:
            aspect_ratio = 540 / height
            image_background = image_background.resize((int(width * aspect_ratio), 540))
        width, height = image_background.size
        if width >= 960:
            left = int((width - 960) / 2)
            top = 0
            right = int((width - 960) / 2 + 960)
            bottom = height
            image_background = image_background.crop((left, top, right, bottom))
            image_background.resize((960, 540))
        dark_right = Image.open(f"templates/background_features/dark-right-side-for-stat.png")
        image_background.paste(dark_right, (0, 0), dark_right)
        if player_stat[0]['avatar'] != "":
            avatar_req = requests.get(player_stat[0]['avatar'], stream=True)
            image_avatar = Image.open(avatar_req.raw)
            image_avatar = image_avatar.resize((130, 130))
        else:
            image_avatar = Image.open(f"templates/question-mark-icon.jpg")
            image_avatar = image_avatar.resize((130, 130))

        image_background.paste(image_avatar, (10, 10))
        draw_image_bg = ImageDraw.Draw(image_background)
        draw_image_bg.text((160, 20), player_stat[0]['nickname'], font=font_name)

        async with aiohttp.ClientSession() as session:
            app_stat = await user_app_stat(session, player_stat[0]["steam_id"])
            rec_pl_stat = await user_rec_played_stat(session, player_stat[0]['steam_id'])

        playtime_2weeks = "Last 2 weeks: Unknown"
        playtime_forever = "Summary in CSGO: Unknown"
        percentage_played = "Activity: Unknown"
        csgotime_played_hrs = "Played in CSGO: Unknown"
        if "response" in rec_pl_stat.keys() and "games" in rec_pl_stat['response'].keys():
            for app in rec_pl_stat['response']['games']:
                if app['appid'] == 730:
                    playtime_2weeks = f"Last 2 weeks: {int(app['playtime_2weeks'] / 60)} hrs"
                    playtime_forever = f"Summary in CSGO: {int(app['playtime_forever'] / 60)} hrs"
                    if app_stat is not None:
                        csgo_playtime = app_stat['playerstats']['stats'][2]['value'] / 60 / 60
                        csgotime_played_hrs = f"Played in CSGO: {int(csgo_playtime)} hrs"
                        percentage_played = f"Activity: " \
                                            f"{csgo_playtime / (app['playtime_forever'] / 60) * 100:.1f}%"
                    else:
                        csgotime_played_hrs = f"Played in CSGO: Unknown"
                        percentage_played = f"Activity: Unknown"

        draw_image_bg.text((10, 150), playtime_2weeks, font=font)
        draw_image_bg.text((10, 180), csgotime_played_hrs, font=font)
        draw_image_bg.text((10, 210), playtime_forever, font=font)
        draw_image_bg.text((10, 240), percentage_played, font=font)

        faceitlvl = player_stat[0]['skill_level']
        image_lvl = Image.open(f"templates/faceit_icons/faceit{faceitlvl}.png").convert("RGBA")
        image_lvl = image_lvl.resize((24, 24))
        image_background.paste(image_lvl, (155, 74), image_lvl)

        draw_image_bg.text((184, 70), str(player_stat[0]['faceit_elo']), font=font)

        mean_k = mean_a = mean_d = mean_kd = mean_kr = mean_hs = total_4k = total_5k = 0
        for i in range(10):
            mean_k += int(player_stat[i]['kills'])
            mean_a += int(player_stat[i]['assists'])
            mean_d += int(player_stat[i]['deaths'])
            mean_kd += float(player_stat[i]['kdratio'])
            mean_kr += float(player_stat[i]['krratio'])
            mean_hs += float(player_stat[i]['headshots%'])
            total_4k += int(player_stat[i]['4k'])
            total_5k += int(player_stat[i]['5k'])

            if float(player_stat[i]['kdratio']) >= 1.3:
                stat_color = (0, 190, 0, 255)
            elif float(player_stat[i]['kdratio']) < 0.6:
                stat_color = (170, 0, 0, 255)
            elif 0.8 > float(player_stat[i]['kdratio']) >= 0.6:
                stat_color = (255, 165, 0, 255)
            else:
                stat_color = (255, 255, 255, 255)

            if player_stat[i]['result'] == "1":
                image_background.paste(win_bg, (775, 50 * i + 24), win_bg)
            else:
                image_background.paste(lose_bg, (775, 50 * i + 24), lose_bg)
            draw_image_bg.text((870, 50 * i + 30), player_stat[i]['mapscore'], font=font)
            current_map = Image.open(f"templates/maps/{player_stat[i]['mapname']}.jpg")
            current_map = current_map.resize((90, 50))
            image_background.paste(current_map, (770, 50 * i + 24))
            kad = f"{player_stat[i]['kills']}/" \
                  f"{player_stat[i]['assists']}/" \
                  f"{player_stat[i]['deaths']}"
            draw_image_bg.text((665, 50 * i + 30), kad, font=font, fill=stat_color)
            dd = datetime.utcfromtimestamp(player_stat[i]['started_at']).strftime("%m/%d")
            cc = calendar.month_name[int(dd.split("/")[0])][:3]
            draw_image_bg.text((570, 50 * i + 30), dd.split("/")[1] + " " + cc, font=font)

        mean_k, mean_a, mean_d, mean_kd, mean_kr, mean_hs = \
            map((lambda x: x / 10), [mean_k, mean_a, mean_d, mean_kd, mean_kr, mean_hs])

        draw_image_bg.text((10, 310), "Last 10 games played:", font=font)
        draw_image_bg.text((10, 340), f"KAD: {mean_k:.1f} / "
                                      f"{mean_a:.1f} / "
                                      f"{mean_d:.1f}", font=font)
        draw_image_bg.text((10, 370), f"K/D: {mean_kd:.2f}", font=font)
        draw_image_bg.text((10, 400), f"K/R: {mean_kr:.2f}", font=font)
        draw_image_bg.text((10, 430), f"Total 4K: {total_4k}", font=font)
        draw_image_bg.text((10, 460), f"Total 5K: {total_5k}", font=font)
        draw_image_bg.text((10, 490), f"HS: {mean_hs:.1f}%", font=font)

        draw_image_bg.text((270, 70),
                           f"{player_stat[0]['region']}: "
                           f"{player_stat[0]['region_place']}",
                           font=font)
        draw_image_bg.text((270, 100),
                           f"{player_stat[0]['country']}: "
                           f"{player_stat[0]['country_place']}",
                           font=font)

        return image_background
