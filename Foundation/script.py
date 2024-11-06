from flask import Flask, request, redirect, session, url_for, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

# Spotify API credentials
SPOTIPY_CLIENT_ID = 'your_client_id'
SPOTIPY_CLIENT_SECRET = 'your_client_secret'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5000/callback'

# Configure Spotify authentication
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="user-top-read"
)

# Initialize database if it doesn't exist
if not os.path.exists("music.db"):
    conn = sqlite3.connect("music.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, spotify_id TEXT, name TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS spotify_data (user_id INTEGER, artist TEXT, track TEXT, 
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.close()

def save_user_data(spotify_id, name, top_artists, top_tracks):
    conn = sqlite3.connect("music.db")
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE spotify_id = ?", (spotify_id,))
    user_id = cursor.fetchone()

    if not user_id:
        cursor.execute("INSERT INTO users (spotify_id, name) VALUES (?, ?)", (spotify_id, name))
        user_id = cursor.lastrowid
    else:
        user_id = user_id[0]

    # Clear existing data to prevent duplicates
    cursor.execute("DELETE FROM spotify_data WHERE user_id = ?", (user_id,))

    # Insert new data
    for artist in top_artists:
        cursor.execute("INSERT INTO spotify_data (user_id, artist, track) VALUES (?, ?, NULL)", (user_id, artist))
    for track in top_tracks:
        cursor.execute("INSERT INTO spotify_data (user_id, artist, track) VALUES (?, NULL, ?)", (user_id, track))

    conn.commit()
    conn.close()

@app.route('/')
def index():
    auth_url = sp_oauth.get_authorize_url()
    return render_template('index.html', auth_url=auth_url)

@app.route('/callback')
def callback():
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_profile = sp.current_user()
    top_artists = sp.current_user_top_artists(limit=10)['items']
    top_tracks = sp.current_user_top_tracks(limit=10)['items']

    artist_names = [artist['name'] for artist in top_artists]
    track_names = [track['name'] for track in top_tracks]

    save_user_data(user_profile['id'], user_profile['display_name'], artist_names, track_names)

    return render_template('profile.html', name=user_profile['display_name'],
                           artist_names=artist_names, track_names=track_names)

if __name__ == '__main__':
    app.run(debug=True)