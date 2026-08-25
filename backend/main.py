from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import subprocess
from fastapi.staticfiles import StaticFiles

app = FastAPI()

UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")

UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)


app.mount(
    "/stream",
    StaticFiles(directory="processed"),
    name="stream"
)

app.mount(
    "/app",
    StaticFiles(directory="static", html=True),
    name="app"
)

@app.get("/")
def root():
    return {"message": "StreamForge API is running"}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    input_path = UPLOAD_DIR / file.filename

    with input_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    video_name = Path(file.filename).stem

    hls_dir = PROCESSED_DIR / video_name / "720p"
    hls_dir.mkdir(parents=True, exist_ok=True)

    playlist_path = hls_dir / "playlist.m3u8"
    segment_pattern = hls_dir / "segment%03d.ts"

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", "scale=-2:720",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-hls_time", "4",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(segment_pattern),
        str(playlist_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="HLS processing failed"
        )

    return {
    "message": "Video converted to HLS successfully",
    "stream_url": f"/stream/{video_name}/720p/playlist.m3u8"
    
    }