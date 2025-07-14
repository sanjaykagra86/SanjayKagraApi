# ✅ FastAPI Transcoder deployable script with HLS streaming on Fly.io

from fastapi import FastAPI, Form
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import subprocess
import uuid
import os
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HLS Transcoder API", description="Transcode 720p m3u8 to lower qualities dynamically", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StreamRequest(BaseModel):
    source_url: str
    quality: str  # '144', '240', '360', '480', '720'

# Ensure streams folder exists
if not os.path.exists("streams"):
    os.makedirs("streams")

@app.get("/")
async def root():
    return {"message": "HLS Transcoder API is live"}

@app.post("/start-stream")
async def start_stream(req: StreamRequest):
    session_id = str(uuid.uuid4())[:8]
    output_dir = f"streams/{session_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Quality map
    quality_map = {
        "144": "256:144",
        "240": "426:240",
        "360": "640:360",
        "480": "854:480",
        "720": "1280:720"
    }
    if req.quality not in quality_map:
        return JSONResponse({"error": "Invalid quality selected."}, status_code=400)

    scale = quality_map[req.quality]

    command = [
        "ffmpeg",
        "-i", req.source_url,
        "-vf", f"scale={scale}",
        "-c:a", "aac",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "delete_segments+omit_endlist",
        f"{output_dir}/index.m3u8"
    ]
    subprocess.Popen(command)

    return {
        "message": "Transcoding started",
        "stream_url": f"/streams/{session_id}/index.m3u8",
        "session_id": session_id
    }

@app.post("/stop-stream")
async def stop_stream(session_id: str = Form(...)):
    folder = f"streams/{session_id}"
    if os.path.exists(folder):
        subprocess.call(["rm", "-rf", folder])
        return {"status": "stopped", "session_id": session_id}
    else:
        return {"error": "Session not found."}

# Serve streams
app.mount("/streams", StaticFiles(directory="streams"), name="streams")
