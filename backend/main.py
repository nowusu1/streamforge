from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from redis import Redis
from rq import Queue, Retry
from datetime import datetime, timezone
import shutil
import uuid
import json
import time


# --------------------------------------------------
# App
# --------------------------------------------------

app = FastAPI()


# --------------------------------------------------
# Directories
# --------------------------------------------------

UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")

UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# Redis
# --------------------------------------------------

# Redis connection for our JSON job data
redis_client = Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# Separate binary-safe Redis connection for RQ
rq_redis = Redis(
    host="localhost",
    port=6379,
    db=0
)


# --------------------------------------------------
# Queue
# --------------------------------------------------

queue = Queue(
    "streamforge",
    connection=rq_redis
)


# --------------------------------------------------
# Static Files
# --------------------------------------------------

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


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def utc_now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def save_job(
    job_id: str,
    job_data: dict
):
    redis_client.set(
        f"job:{job_id}",
        json.dumps(job_data)
    )


def get_job(
    job_id: str
):
    raw_job = redis_client.get(
        f"job:{job_id}"
    )

    if raw_job is None:
        return None

    return json.loads(
        raw_job
    )


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
def root():

    try:
        redis_client.ping()
        redis_status = "connected"

    except Exception:
        redis_status = "unavailable"

    return {
        "message": "StreamForge API is running",
        "redis": redis_status,
        "queue": "streamforge"
    }


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...)
):

    video_id = str(
        uuid.uuid4()
    )

    job_id = str(
        uuid.uuid4()
    )


    original_extension = (
        Path(file.filename).suffix
        or ".mp4"
    )


    input_path = (
        UPLOAD_DIR /
        f"{video_id}{original_extension}"
    )


    with input_path.open(
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    queued_timestamp = time.time()


    job_data = {

        "job_id":
            job_id,

        "video_id":
            video_id,

        "original_filename":
            file.filename,

        "status":
            "queued",

        "stream_url":
            None,

        "renditions":
            [],

        "source_resolution":
            None,

        "queued_at":
            utc_now_iso(),

        "queued_timestamp":
            queued_timestamp,

        "started_at":
            None,

        "completed_at":
            None,

        "metrics": {

            "queue_wait_seconds":
                None,

            "total_processing_seconds":
                None,

            "rendition_processing_seconds":
                {}
        },

        "error":
            None
    }


    save_job(
        job_id,
        job_data
    )


    queue.enqueue(

        "worker.process_video_job",

        job_id,

        video_id,

        str(input_path),

        job_id=job_id,

        job_timeout=1800,

        retry=Retry(
            max=3,
            interval=[
                5,
                10,
                20
            ]
        )
    )


    return {

        "message":
            "Video accepted for processing",

        "job_id":
            job_id,

        "video_id":
            video_id,

        "status":
            "queued"
    }


@app.get("/jobs/{job_id}")
def get_job_status(
    job_id: str
):

    job = get_job(
        job_id
    )


    if job is None:

        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )


    return job