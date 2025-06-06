import time
import os
import requests
import pandas as pd
from datetime import datetime

# === Get Spotify Credentials from Environment (for GitHub Actions) ===
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']

# === Playlist ID (Top 200 Global) ===
PLAYLIST_ID = '4yNfFAuHcSgzbcSm6q5QDu'

# === Step 1: Get Access Token ===
def get_spotify_token(client_id, client_secret):
    url = 'https://accounts.spotify.com/api/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials'}
    response = requests.post(url, headers=headers, data=data, auth=(client_id, client_secret))
    return response.json()['access_token']

# === Step 2: Fetch Playlist Tracks ===
def get_playlist_tracks(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {'Authorization': f'Bearer {token}'}
    
    all_items = []
    offset = 0
    limit = 100

    while True:
        params = {'limit': limit, 'offset': offset}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("Error:", response.status_code, response.text)
            break

        data = response.json()
        items = data.get('items', [])
        all_items.extend(items)

        if len(items) < limit:
            break
        offset += limit
        time.sleep(0.1)

    print(f"✅ Total tracks retrieved: {len(all_items)}")

    track_data = []
    artist_info = []

    for item in all_items:
        track = item.get('track')
        if track:
            track_id = track.get('id')
            artist = track['artists'][0]
            artist_id = artist.get('id')
            artist_name = artist.get('name')
            image_url = track['album']['images'][0]['url'] if track['album']['images'] else None

            if track_id and artist_id:
                track_data.append({
                    'track_id': track_id,
                    'track_name': track.get('name', 'Unknown'),
                    'artist_name': artist_name or 'Unknown',
                    'artist_id': artist_id,
                    'album_name': track['album'].get('name', 'Unknown'),
                    'release_date': track['album'].get('release_date', None),
                    'popularity': track.get('popularity', None),
                    'cover_url': image_url,
                    'spotify_url': track['external_urls'].get('spotify')
                })
                artist_info.append((artist_id, artist_name))

    df_tracks = pd.DataFrame(track_data)
    return df_tracks, dict(set(artist_info))

# === Step 3: Fetch Artist Images ===
def fetch_artist_images(artist_dict, token):
    headers = {'Authorization': f'Bearer {token}'}
    artist_image_data = {}

    for artist_id, artist_name in artist_dict.items():
        url = f'https://api.spotify.com/v1/artists/{artist_id}'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            artist_data = response.json()
            images = artist_data.get('images', [])
            artist_image_data[artist_id] = images[0]['url'] if images else None
        else:
            print(f"❌ Could not fetch image for {artist_name} ({artist_id})")
            artist_image_data[artist_id] = None
        time.sleep(0.1)

    return artist_image_data

# === Main Workflow ===
if __name__ == "__main__":
    token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
    df_tracks, artist_dict = get_playlist_tracks(token, PLAYLIST_ID)
    artist_images = fetch_artist_images(artist_dict, token)

    # Merge artist image URL
    df_tracks['artist_image_url'] = df_tracks['artist_id'].map(artist_images)

    # Final columns
    columns_to_keep = [
        'track_id', 'track_name', 'artist_name', 'album_name', 'release_date',
        'popularity', 'cover_url', 'spotify_url', 'artist_image_url'
    ]

    df_final = df_tracks[columns_to_keep].fillna('')  # Handle missing values

    df_final['data_refresh_timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Export to CSV in project root (GitHub will track this)
    df_final.to_csv('spotify_playlist_data.csv', index=False)

    print("✅ Final CSV with artist images saved as spotify_playlist_data.csv")
    print(df_final.head())
