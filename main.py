from flask import Flask, render_template
import requests
from google.cloud import datastore
from time import time

SAVE_TIME = 300

datastore_client = datastore.Client()
app = Flask(__name__, instance_relative_config=True)

app.config.from_pyfile('config.py')

def short(str):
    if len(str) > 29:
        str = str[:29]

    return str

app.jinja_env.filters['short'] = short

streams = {}
token = {}

@app.route('/')
def index():
    return render_template("index.html", logins=get_logins(),
            streams=get_streams().get('data', []))

def get_logins():
    
    query = datastore_client.query(kind='logins')
    logins = [login['login'] for login in query.fetch()]
    
    return logins

def get_streams():
    
    since_call = time() - streams.get('time', 0)
    if since_call < SAVE_TIME:
        return streams
    
    logins = get_logins()

    headers = {'Client-ID': app.config['TWITCH_CLIENT_ID'],
            'Authorization': auth()}
    params = {"user_login": logins}
    
    streams_twitch = requests.get('https://api.twitch.tv/helix/streams',
                                 params=params, headers=headers)
    
    if streams_twitch.status_code != requests.codes.ok:
        return streams
	
    streams['data'] = streams_twitch.json()['data'].copy()
    
    games_ids = []
    
    for stream in streams['data']:
    	games_ids.append(stream['game_id'])
        
    games = get_games(games_ids)
    
    for stream in streams['data']:
        stream['game_name'] = games.get(stream['game_id'], 'Dota 2')
        
    streams['time'] = time()
        
    return streams

def get_games(games_ids):
    
    if not games_ids:
        return {}

    headers = {'Client-ID': app.config['TWITCH_CLIENT_ID'],
            'Authorization': auth()}
    params = {'id': games_ids}
    games_twitch = requests.get('https://api.twitch.tv/helix/games',
                     params=params, headers=headers)
    
    if games_twitch.status_code != requests.codes.ok:
        return {}
    
    games = {}
    
    for game in games_twitch.json()['data']:
    	games[game['id']] = game['name']
        
    return games

def auth():
    global token

    if token:
        return f"{'B' + token['token_type'][1:]} {token['access_token']}"

    params = {'client_id': app.config['TWITCH_CLIENT_ID'],
            'client_secret': app.config['TWITCH_SECRET'],
            'grant_type': 'client_credentials'}
    token_answ = requests.post("https://id.twitch.tv/oauth2/token", data=params)

    if token_answ.status_code != requests.codes.ok:
        return ''

    token = token_answ.json()

    return f"{'B' + token['token_type'][1:]} {token['access_token']}"

