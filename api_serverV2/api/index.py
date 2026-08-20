from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import uvicorn
import os
import re
import requests
import urllib.parse

app = FastAPI(
    title="YouTube Music REST API V2",
    description="API gratis dan cepat untuk mengambil data dari YouTube Music dan serve frontend StarMusify.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ytmusic = YTMusic()

@app.get("/")
@app.get("/api")
def root_api():
    return {"status": True, "message": "API V2 Running"}

@app.get("/api/search")
def search(q: str = None, query: str = None):
    actual_q = q or query
    if not actual_q:
        return {"status": False, "result": {"songs": [], "playlists": [], "artists": []}}
    try:
        res = ytmusic.search(actual_q, limit=20)
        songs, playlists, artists = [], [], []
        for s in res:
            rt = s.get('resultType')
            thumb = s.get('thumbnails', [{}])[-1].get('url', '')
            if rt in ('song', 'video'):
                songs.append({
                    "videoId": s.get('videoId'),
                    "title": s.get('title'),
                    "artist": ", ".join([a.get('name', '') for a in s.get('artists', [])]),
                    "artistId": s.get('artists', [{}])[0].get('id', '') if s.get('artists') else '',
                    "cover": thumb,
                    "url": "https://youtube.com/watch?v=" + str(s.get('videoId', ''))
                })
            elif rt == 'playlist':
                bid = s.get('browseId') or s.get('playlistId')
                playlists.append({
                    "id": bid,
                    "title": s.get('title'),
                    "cover": thumb,
                    "url": "https://youtube.com/playlist?list=" + str(bid)
                })
            elif rt == 'artist':
                bid = s.get('browseId')
                artists.append({
                    "id": bid,
                    "name": s.get('artist'),
                    "cover": thumb,
                    "url": "https://youtube.com/channel/" + str(bid)
                })
        return {"status": True, "result": {"songs": songs, "playlists": playlists, "artists": artists}}
    except Exception as e:
        return {"status": False, "result": {"songs": [], "playlists": [], "artists": []}}

@app.get("/api/artist")
def get_artist(id: str = Query(...)):
    try:
        if id.startswith("MPRE"):
            data = ytmusic.get_album(id)
            songs = []
            album_thumb = data.get('thumbnails', [{}])[-1].get('url', '') if data.get('thumbnails') else ''
            for tr in data.get('tracks', []):
                songs.append({
                    "videoId": tr.get('videoId'),
                    "title": tr.get('title'),
                    "artist": ", ".join([a.get('name', '') for a in tr.get('artists', [])]) if tr.get('artists') else 'Unknown',
                    "cover": album_thumb,
                    "url": "https://youtube.com/watch?v=" + str(tr.get('videoId'))
                })
            return {
                "status": True, 
                "result": {
                    "name": data.get('title', 'Unknown Album'),
                    "cover": album_thumb,
                    "songs": songs
                }
            }
        elif id.startswith("VLPL"):
            data = ytmusic.get_playlist(id)
            songs = []
            for tr in data.get('tracks', []):
                thumb = tr.get('thumbnails', [{}])[-1].get('url', '')
                songs.append({
                    "videoId": tr.get('videoId'),
                    "title": tr.get('title'),
                    "artist": ", ".join([a.get('name', '') for a in tr.get('artists', [])]) if tr.get('artists') else 'Unknown',
                    "cover": thumb,
                    "url": "https://youtube.com/watch?v=" + str(tr.get('videoId'))
                })
            return {
                "status": True, 
                "result": {
                    "name": data.get('title', 'Unknown Playlist'),
                    "cover": data.get('thumbnails', [{}])[-1].get('url', '') if data.get('thumbnails') else '',
                    "songs": songs
                }
            }
        else:
            try:
                data = ytmusic.get_artist(id)
                songs = []
                for tr in data.get('songs', {}).get('results', []):
                    thumb = tr.get('thumbnails', [{}])[-1].get('url', '')
                    songs.append({
                        "videoId": tr.get('videoId'),
                        "title": tr.get('title'),
                        "artist": ", ".join([a.get('name', '') for a in tr.get('artists', [])]) if tr.get('artists') else 'Unknown',
                        "cover": thumb,
                        "url": "https://youtube.com/watch?v=" + str(tr.get('videoId'))
                    })
                return {
                    "status": True,
                    "result": {
                        "name": data.get('name', 'Unknown Artist'),
                        "cover": data.get('thumbnails', [{}])[-1].get('url', '') if data.get('thumbnails') else '',
                        "songs": songs
                    }
                }
            except Exception as e:
                # Fallback menggunakan yt-dlp karena ytmusicapi sedang error untuk halaman artis (KeyError: 'contents')
                try:
                    import yt_dlp
                    ydl_opts = {
                        'extract_flat': True,
                        'quiet': True,
                        'no_warnings': True,
                        'playlist_end': 15
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(f"https://www.youtube.com/channel/{id}", download=False)
                        songs = []
                        for e in info.get('entries', []):
                            if not e or not e.get('id'): continue
                            thumb = e.get('thumbnails', [{}])[-1].get('url', '') if e.get('thumbnails') else ''
                            songs.append({
                                "videoId": e.get('id'),
                                "title": e.get('title'),
                                "artist": e.get('uploader') or info.get('uploader') or 'Unknown',
                                "cover": thumb,
                                "url": "https://youtube.com/watch?v=" + str(e.get('id'))
                            })
                        
                        cover_url = ""
                        if info.get('thumbnails'):
                            cover_url = info.get('thumbnails', [{}])[-1].get('url', '')
                            
                        # Bersihkan nama artis dari string "Uploads from " dan " - Topic"
                        raw_name = info.get('uploader') or info.get('title', '') or 'Unknown Artist'
                        clean_name = raw_name.replace('Uploads from ', '').replace(' - Topic', '')
                            
                        return {
                            "status": True,
                            "result": {
                                "name": clean_name,
                                "cover": cover_url,
                                "songs": songs
                            }
                        }
                except Exception as ex:
                    return {"status": False, "result": {}}
    except Exception as e:
        return {"status": False, "result": {}}

@app.get("/api/album/{browse_id}")
def get_album_detail(browse_id: str):
    # Endpoint ini persis sama dengan /api/artist untuk MPRE/VLPL
    # Karena web player (album.js) langsung memanggil fetch('/api/album/...')
    return get_artist(id=browse_id)

@app.get("/api/suggest")
def get_suggestions(q: str = None, query: str = None):
    actual_q = q or query
    if not actual_q:
        return {"status": False, "result": []}
    try:
        suggestions = ytmusic.get_search_suggestions(actual_q)
        return {"status": True, "result": suggestions}
    except Exception as e:
        return {"status": False, "result": []}

@app.get("/api/lyrics")
def get_lyrics(title: str = None, artist: str = None, q: str = None):
    query = q or f"{title} {artist or ''}"
    q_enc = urllib.parse.quote(query)
    try:
        res = requests.get(f"https://lrclib.net/api/search?q={q_enc}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                lyrics = data[0].get('syncedLyrics') or data[0].get('plainLyrics')
                if lyrics:
                    lines = []
                    l_type = 'text'
                    time_regex = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\]')
                    for rl in lyrics.split('\n'):
                        m = time_regex.search(rl)
                        if m:
                            l_type = 'synced'
                            time_sec = int(m.group(1)) * 60 + int(m.group(2)) + float("0." + (m.group(3) or "0"))
                            text = time_regex.sub('', rl).strip()
                            if text:
                                lines.append({"text": text, "time": time_sec})
                        elif rl.strip():
                            lines.append({"text": rl.strip(), "time": 0})
                    if not lines:
                        lines = [{"text": lyrics, "time": 0}]
                    return {"status": True, "result": {"lyrics": {"type": l_type, "lines": lines}}}
    except Exception:
        pass
    return {"status": False, "result": None}

import yt_dlp
from fastapi.responses import StreamingResponse

@app.get("/api/ytplay")
@app.post("/api/ytplay")
async def ytplay(request: Request):
    if request.method == "POST":
        try:
            data = await request.json()
            url = data.get("query") or data.get("url") or ""
        except:
            url = ""
    else:
        url = request.query_params.get("url") or request.query_params.get("query") or ""
        
    video_id = url.split("v=")[-1] if url and "v=" in url else ""
    if "&" in video_id:
        video_id = video_id.split("&")[0]
        
    if not video_id:
        if request.method == "POST":
            try:
                data = await request.json()
                video_id = data.get("videoId") or ""
            except:
                pass
        else:
            video_id = request.query_params.get("videoId") or ""

    if not video_id:
        return {"status": False, "result": {}}
        
    host_url = str(request.base_url).rstrip("/")
    return {
        "status": True,
        "result": {
            "title": "Audio",
            "download": {
                # Menggunakan backend proxy stream agar terhindar dari batasan IP yt-dlp dan IFrame yang buggy
                "audio": f"{host_url}/api/stream/{video_id}"
            }
        }
    }

@app.get("/api/stream/{video_id}")
def stream_audio(video_id: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            audio_url = info.get('url')
            
            if not audio_url:
                raise HTTPException(status_code=404, detail="Audio stream not found")
                
            def generate_audio():
                with requests.get(audio_url, stream=True) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                            
            return StreamingResponse(
                generate_audio(), 
                media_type="audio/mp4",
                headers={"Accept-Ranges": "bytes"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("index:app", host="0.0.0.0", port=port, reload=True)
