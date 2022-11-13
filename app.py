from flask import Flask, session, request, redirect, url_for
from os import path, urandom
from json import load, loads, dump
from time import sleep
from urllib import parse
import urllib.request

filepath = path.dirname(path.abspath(__file__))

with open(f"{filepath}/secret.json", "r") as f:
    config = load(f)

CLIENT_ID = config["CLIENT_ID"]
CLIENT_SECRET = config["CLIENT_SECRET"]

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"

REDIRECT_URI = "http://127.0.0.1:5000/callback/q"
SCOPE = "playlist-read-private playlist-read-collaborative"

auth_query_params = {
    "client_id": CLIENT_ID,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
}

app = Flask(__name__)
app.secret_key = urandom(32)


def urlify_query_params(params):
    return "&".join([f"{k}={parse.quote(v)}" for k, v in params.items()])


def api_query(url):
    auth_header = {"Authorization": f"Bearer {session['access_token']}"}
    req = urllib.request.Request(url, headers=auth_header, method="GET")
    req = urllib.request.urlopen(req)
    res = req.read()
    return loads(res)


@app.route("/")
def root():
    url_args = urlify_query_params(auth_query_params)
    return redirect(f"{AUTH_URL}/?{url_args}")


@app.route("/callback/q")
def callback():
    auth_token = request.args["code"]
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    req = urllib.request.Request(TOKEN_URL, data=parse.urlencode(code_payload).encode())
    req = urllib.request.urlopen(req)
    res = req.read()
    res = loads(res)

    access_token = res["access_token"]
    # refresh_token = res["refresh_token"]
    # token_type = res["token_type"]
    # expires_in = res["expires_in"]

    session["access_token"] = access_token
    return redirect(url_for("data"))


def process_tracks_batch(tracks, accumulator):
    tracks = [track for track in tracks if track["track"]["id"] != None]

    sleep(0.75)
    query_params = urlify_query_params(
        {"ids": ",".join([track["track"]["id"] for track in tracks])}
    )
    features_res = api_query(f"{API_URL}/audio-features?{query_params}")
    audio_features = features_res["audio_features"]

    for i in range(len(tracks)):
        track = tracks[i]
        info = track["track"]
        features = audio_features[i]
        image = None
        if len(info["album"]["images"]) > 0:
            image = info["album"]["images"][0]["url"]
        accumulator.append(
            {
                "id": info["id"],
                "name": info["name"],
                "artists": [artist["name"] for artist in info["artists"]],
                "popularity": info["popularity"],
                "duration_ms": info["duration_ms"],
                "added_at": track["added_at"],
                "danceability": features["danceability"],
                "energy": features["energy"],
                "key": features["key"],
                "loudness": features["loudness"],
                "mode": features["mode"],
                "speechiness": features["speechiness"],
                "acousticness": features["acousticness"],
                "instrumentalness": features["instrumentalness"],
                "liveness": features["liveness"],
                "valence": features["valence"],
                "tempo": features["tempo"],
                "time_signature": features["time_signature"],
                "image": image,
                "album_name": info["album"]["name"],
            }
        )
    return accumulator


def process_tracks(tracks_url):
    playlist_tracks = list()
    sleep(0.75)
    tracks_res = api_query(tracks_url)
    playlist_tracks = process_tracks_batch(tracks_res["items"], playlist_tracks)

    while tracks_res["next"] != None:
        sleep(0.75)
        tracks_url = tracks_res["next"]
        tracks_res = api_query(tracks_url)
        playlist_tracks = process_tracks_batch(tracks_res["items"], playlist_tracks)
    return playlist_tracks


def process_playlist_batch(playlists, accumulator):
    for playlist in playlists:
        if playlist["owner"]["display_name"] == "Eric Lau":
            playlist_dict = {
                "name": playlist["name"],
                "cover": playlist["images"][0]["url"]
                if len(playlist["images"]) > 0
                else None,
            }

            print(playlist["name"])

            playlist_tracks = list()
            if playlist["tracks"]["total"] > 0:
                playlist_tracks = process_tracks(playlist["tracks"]["href"])

            playlist_dict["tracks"] = playlist_tracks
            accumulator.append(playlist_dict)
    return accumulator


@app.route("/data")
def data():
    query_params = urlify_query_params({"offset": "0", "limit": "50"})

    my_playlists = list()

    playlist_url = f"{API_URL}/me/playlists?{query_params}"
    playlist_res = api_query(playlist_url)

    my_playlists = process_playlist_batch(playlist_res["items"], my_playlists)

    while playlist_res["next"] != None:
        sleep(0.75)
        playlist_url = playlist_res["next"]
        playlist_res = api_query(playlist_url)
        my_playlists = process_playlist_batch(playlist_res["items"], my_playlists)

    with open(f"{filepath}/data/raw_api_data.json", "w") as rawdata:
        dump(my_playlists, rawdata, ensure_ascii=False, indent=2)

    return {"playlists": my_playlists}


if __name__ == "__main__":
    app.run(debug=True)
