from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import uvicorn
import os

app = FastAPI(
    title="YouTube Music REST API V2 by Zett",
    description="API gratis dan cepat untuk mengambil data dari YouTube Music dan serve frontend StarMusify.",
    version="2.0.0"
)

# Konfigurasi CORS agar API bisa diakses dari frontend mana saja
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ytmusic = YTMusic()

def format_response(status="success", data=None, **kwargs):
    response = {
        "status": status,
        "creator": "by zett"
    }
    if data is not None:
        response["data"] = data
    response.update(kwargs)
    return response

@app.get("/")
@app.get("/api")
def root_api():
    return format_response(
        message="Welcome to YouTube Music REST API V2 by Zett. Visit /docs for documentation.",
        documentation="/docs"
    )

@app.get("/api/search")
def search(q: str = Query(..., description="Kata kunci pencarian"), type: str = Query("songs", description="Tipe pencarian (songs/albums)")):
    try:
        results = ytmusic.search(q, filter=type, limit=10)
        return format_response(data=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/song/{video_id}")
def get_song_detail(video_id: str):
    try:
        details = ytmusic.get_song(video_id)
        return format_response(data=details)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lyrics/{video_id}")
def get_lyrics(video_id: str):
    try:
        watch_playlist = ytmusic.get_watch_playlist(videoId=video_id)
        lyrics_id = watch_playlist.get('lyrics')
        
        if lyrics_id:
            lyrics_data = ytmusic.get_lyrics(lyrics_id)
            return format_response(video_id=video_id, lyrics=lyrics_data.get('lyrics', ''))
        else:
            return format_response(status="not_found", message="Lirik tidak tersedia.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/album/{browse_id}")
def get_album_detail(browse_id: str):
    try:
        if browse_id.startswith("MPRE"):
            data = ytmusic.get_album(browse_id)
        else:
            data = ytmusic.get_playlist(browse_id)
            
        return format_response(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/play/{video_id}")
def play_audio(video_id: str):
    return format_response(
        message="URL Streaming Web",
        url=f"https://music.youtube.com/watch?v={video_id}"
    )

@app.get("/api/suggest")
def get_suggestions(q: str):
    try:
        suggestions = ytmusic.get_search_suggestions(q)
        return format_response(data=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/artist")
def get_artist(id: str):
    try:
        artist_data = ytmusic.get_artist(id)
        return format_response(data=artist_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ytplay")
def ytplay(url: str = None, video_id: str = None):
    import requests
    try:
        # Menghandle parameter url atau video_id
        if url:
            yt_url = url
        elif video_id:
            yt_url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            raise HTTPException(status_code=400, detail="Harap sediakan parameter url atau video_id")
            
        api_url = f"https://star-cloud.web.id/api/ytplay?url={yt_url}"
        
        response = requests.get(api_url)
        data = response.json()
        
        if data.get("status") and "result" in data and "download" in data["result"]:
            return format_response(
                message="Sukses mengambil data media",
                result=data["result"]
            )
        else:
            return format_response(status="error", message="Format respons tidak sesuai ekspektasi.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil play data: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("index:app", host="0.0.0.0", port=port, reload=True)
