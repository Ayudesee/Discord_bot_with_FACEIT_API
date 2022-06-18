import os
import sqlite3
import psycopg2
# from env_variables import faceit_headers
from decouple import config
import aiohttp
import asyncio

from api_funcs.async_faceit_get_funcs import player_details_by_id, match_stats


async def db_match_finished(request, statistics):
    with sqlite3.connect("stats.sqlite3") as connection:
        cursor = connection.cursor()
        async with aiohttp.ClientSession(headers=config('faceit_headers')) as session:
            for idx_match, match in enumerate(statistics['rounds']):
                cursor.execute('''INSERT OR IGNORE INTO matches(match_faceit_id, date)
                                  VALUES (?, ?)''', [match['match_id'], request['timestamp']])
                for idx_team, team in enumerate(match['teams']):
                    for idx_player, player in enumerate(team['players']):
                        player_elo = int(
                            (await player_details_by_id(session, player['player_id']))['games']['csgo']['faceit_elo'])
                        cursor.execute('''INSERT OR IGNORE INTO players(faceit_id)
                                          VALUES (?)''', [player['player_id']])
                        connection.commit()
                        cursor.execute('''INSERT OR IGNORE INTO elo(player_id, match_id, elo)
                                          VALUES ((SELECT id FROM players
                                                   WHERE faceit_id=?),
                                                  (SELECT id from matches
                                                   WHERE match_faceit_id=?),
                                                   ?)''', [player['player_id'], match['match_id'], player_elo])


def db_fetch_data(pl_items: int = 50, mc_items: int = 50, elo_items: int = 50):
    with sqlite3.connect("stats.sqlite3") as connection:
        cursor = connection.cursor()
        cursor.execute('''SELECT * FROM players LIMIT ?''', [pl_items])
        players_data = cursor.fetchall()
        cursor.execute('''SELECT * FROM matches LIMIT ?''', [mc_items])
        matches_data = cursor.fetchall()
        cursor.execute('''SELECT * FROM elo LIMIT ?''', [elo_items])
        elo_data = cursor.fetchall()
        return players_data, matches_data, elo_data


async def dbps_match_finished(request, statistics):
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    async with aiohttp.ClientSession(headers=config('faceit_headers')) as session:
        for idx_match, match in enumerate(statistics['rounds']):
            cursor.execute('''INSERT INTO matches(match_id, date)
                              VALUES (%s, %s)
                              ON CONFLICT DO NOTHING;''', [match['match_id'], request['timestamp']])
            for idx_team, team in enumerate(match['teams']):
                for idx_player, player in enumerate(team['players']):
                    player_elo = int(
                        (await player_details_by_id(session, player['player_id']))['games']['csgo']['faceit_elo'])
                    cursor.execute('''INSERT INTO players(faceit_id)
                                      VALUES (%s)
                                      ON CONFLICT DO NOTHING;''', [player['player_id']])
                    conn.commit()
                    cursor.execute('''INSERT INTO elos(player_id, match_id, elo)
                                      VALUES (
                                      (SELECT id FROM players
                                      WHERE faceit_id=%s),
                                      (SELECT id from matches
                                      WHERE match_id=%s),
                                      %s)
                                      ON CONFLICT DO NOTHING;''',
                                   [player['player_id'], match['match_id'], player_elo])
            conn.commit()


def dbps_fetch_data(pl_items: int = 50, mc_items: int = 50, elo_items: int = 50):
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM players LIMIT {}'''.format(pl_items))
    players_data = cursor.fetchall()
    cursor.execute('''SELECT * FROM matches LIMIT {}'''.format(mc_items))
    matches_data = cursor.fetchall()
    cursor.execute('''SELECT * FROM elos LIMIT {}'''.format(elo_items))
    elo_data = cursor.fetchall()
    return players_data, matches_data, elo_data
