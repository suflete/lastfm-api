from flask import Flask, request, jsonify
import requests
import toml
from base64 import b64encode

config = toml.load("config.toml")
app = Flask(__name__)

LASTFM_API_KEY = config['LASTFM_API_KEY']
SPOTIFY_CLIENT_ID = config['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = config['SPOTIFY_CLIENT_SECRET']

def get_spotify_token():
    auth_url = "https://accounts.spotify.com/api/token"
    auth_header = b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode("utf-8")
    response = requests.post(auth_url, headers={"Authorization": f"Basic {auth_header}"}, data={"grant_type": "client_credentials"})
    return response.json().get("access_token")

def get_spotify_track_info(track_name, artist_name):
    access_token = get_spotify_token()
    if not access_token:
        return None, None
    headers = {"Authorization": f"Bearer {access_token}"}
    query = f"track:{track_name} artist:{artist_name}"
    response = requests.get(f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1", headers=headers)
    if response.status_code == 200:
        results = response.json().get("tracks", {}).get("items")
        if results:
            track_url = results[0]["external_urls"]["spotify"]
            preview_url = results[0].get("preview_url")
            return track_url, preview_url
    return None, None

@app.route('/lastfm/listening')
def lastfm_listening():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "No Last.fm username provided"}), 400

    url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key={LASTFM_API_KEY}&format=json&limit=1"
    response = requests.get(url)
    
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch data from Last.fm"}), response.status_code
    
    data = response.json()

    try:
        recent_tracks = data['recenttracks']['track']
        if not recent_tracks:
            return jsonify({"error": "User is not listening to something currently"}), 404

        current_track = recent_tracks[0]
        is_now_playing = current_track.get('@attr', {}).get('nowplaying') == 'true'

        if not is_now_playing:
            return jsonify({"error": "User is not listening to something currently"}), 404

        track_name = current_track["name"]
        artist_name = current_track["artist"]["#text"]
        spotify_url, preview_url = get_spotify_track_info(track_name, artist_name)

        track_info = {
            "track_name": track_name,
            "artist": artist_name,
            "album": current_track["album"]["#text"],
            "track_url": current_track["url"],
            "cover_image": current_track["image"][-1]["#text"] if current_track["image"] else None,
            "spotify_url": spotify_url,
            "preview_url": preview_url
        }
        return jsonify(track_info)

    except (KeyError, IndexError) as e:
        return jsonify({"error": "Unexpected response format", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host=config['host'], port=config['port'])
