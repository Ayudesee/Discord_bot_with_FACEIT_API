import json
from decouple import config
# from env_variables import steam_token


base_url = "https://api.steampowered.com/"
user_stats_url = base_url + "ISteamUserStats/GetUserStatsForGame/v2/"
player_service_url = base_url + "IPlayerService/GetRecentlyPlayedGames/v0001/"


async def user_app_stat(session, steamid, appid=730):
    if steamid is None:
        return None

    api_url = f"{user_stats_url}?key={config('steam_token')}&steamid={steamid}&appid={appid}"
    async with session.get(api_url) as res:
        if res.status == 200:
            bin_data = await res.read()
            return json.loads(bin_data.decode())
        else:
            return None


async def user_rec_played_stat(session, steamid=""):
    api_url = f"{player_service_url}?key={config('steam_token')}&steamid={steamid}&format=json"
    if steamid is None:
        return None

    async with session.get(api_url) as res:
        if res.status == 200:
            bin_data = await res.read()
            return json.loads(bin_data.decode())
        else:
            return None
