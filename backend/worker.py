from pathlib import Path
from redis import Redis
from datetime import datetime, timezone
import subprocess
import json
import time


# --------------------------------------------------
# Directories
# --------------------------------------------------

PROCESSED_DIR = Path("processed")

PROCESSED_DIR.mkdir(
    exist_ok=True
)


# --------------------------------------------------
# Redis
# --------------------------------------------------

redis_client = Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)


# --------------------------------------------------
# General Helpers
# --------------------------------------------------

def utc_now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def make_even(
    value: float
):
    rounded = int(
        round(value)
    )

    if rounded % 2 != 0:
        rounded += 1

    return max(
        rounded,
        2
    )


# --------------------------------------------------
# Job Helpers
# --------------------------------------------------

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


def save_job(
    job_id: str,
    job_data: dict
):

    redis_client.set(
        f"job:{job_id}",
        json.dumps(job_data)
    )


def update_job(
    job_id: str,
    **updates
):

    job = get_job(
        job_id
    )

    if job is None:
        return

    job.update(
        updates
    )

    save_job(
        job_id,
        job
    )


# --------------------------------------------------
# Detect Video Resolution
# --------------------------------------------------

def get_video_resolution(
    input_path: Path
):

    command = [

        "ffprobe",

        "-v",
        "error",

        "-select_streams",
        "v:0",

        "-show_entries",
        "stream=width,height",

        "-of",
        "json",

        str(input_path)
    ]


    result = subprocess.run(

        command,

        stdin=subprocess.DEVNULL,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        text=True
    )


    if result.returncode != 0:

        raise RuntimeError(
            "Could not detect video resolution"
        )


    data = json.loads(
        result.stdout
    )


    streams = data.get(
        "streams",
        []
    )


    if not streams:

        raise RuntimeError(
            "No video stream found"
        )


    width = streams[0].get(
        "width"
    )

    height = streams[0].get(
        "height"
    )


    if not width or not height:

        raise RuntimeError(
            "Video resolution unavailable"
        )


    return width, height


# --------------------------------------------------
# Select Renditions
# --------------------------------------------------

def get_renditions(
    source_width: int,
    source_height: int
):

    rendition_profiles = {

        "1080p": {
            "height": 1080,
            "bandwidth": 5000000
        },

        "720p": {
            "height": 720,
            "bandwidth": 2800000
        },

        "480p": {
            "height": 480,
            "bandwidth": 1400000
        }
    }


    selected = {}


    for label, settings in (
        rendition_profiles.items()
    ):

        target_height = (
            settings["height"]
        )


        # Prevent unnecessary upscaling
        if source_height < target_height:
            continue


        aspect_ratio = (
            source_width /
            source_height
        )


        target_width = make_even(
            target_height *
            aspect_ratio
        )


        selected[label] = {

            "width":
                target_width,

            "height":
                target_height,

            "bandwidth":
                settings["bandwidth"],

            "resolution":
                f"{target_width}x{target_height}"
        }


    # Handle sources smaller than 480p
    if not selected:

        output_width = make_even(
            source_width
        )

        output_height = make_even(
            source_height
        )


        selected["source"] = {

            "width":
                output_width,

            "height":
                output_height,

            "bandwidth":
                800000,

            "resolution":
                f"{output_width}x{output_height}"
        }


    return selected


# --------------------------------------------------
# Main Worker
# --------------------------------------------------

def process_video_job(
    job_id: str,
    video_id: str,
    input_path_string: str
):

    input_path = Path(
        input_path_string
    )


    job = get_job(
        job_id
    )


    if job is None:

        raise RuntimeError(
            f"Job {job_id} was not found"
        )


    processing_started = (
        time.perf_counter()
    )


    queued_timestamp = job.get(
        "queued_timestamp"
    )


    if queued_timestamp is not None:

        queue_wait_seconds = (
            time.time()
            - queued_timestamp
        )

    else:

        queue_wait_seconds = None


    metrics = job.get(
        "metrics",
        {}
    )


    metrics[
        "queue_wait_seconds"
    ] = (
        round(
            queue_wait_seconds,
            3
        )
        if queue_wait_seconds
        is not None
        else None
    )


    metrics[
        "rendition_processing_seconds"
    ] = {}


    try:

        update_job(

            job_id,

            status="processing",

            started_at=utc_now_iso(),

            metrics=metrics,

            error=None
        )


        print(
            "\n------------------------------"
        )

        print(
            "STREAMFORGE WORKER"
        )

        print(
            "------------------------------"
        )


        print(
            f"Job ID: {job_id}"
        )

        print(
            f"Video ID: {video_id}"
        )


        if queue_wait_seconds is not None:

            print(
                "Queue wait time: "
                f"{queue_wait_seconds:.3f}s"
            )


        # --------------------------------------------------
        # Source Resolution
        # --------------------------------------------------

        source_width, source_height = (
            get_video_resolution(
                input_path
            )
        )


        print(
            "Source resolution: "
            f"{source_width}x{source_height}"
        )


        renditions = get_renditions(
            source_width,
            source_height
        )


        print(
            "Selected renditions: "
            + ", ".join(
                renditions.keys()
            )
        )


        for label, settings in (
            renditions.items()
        ):

            print(
                f"{label}: "
                f"{settings['resolution']}"
            )


        update_job(

            job_id,

            source_resolution=(
                f"{source_width}x{source_height}"
            ),

            renditions=list(
                renditions.keys()
            )
        )


        # --------------------------------------------------
        # Output Directory
        # --------------------------------------------------

        video_root = (
            PROCESSED_DIR /
            video_id
        )


        video_root.mkdir(
            parents=True,
            exist_ok=True
        )


        # --------------------------------------------------
        # Generate HLS Renditions
        # --------------------------------------------------

        for label, settings in (
            renditions.items()
        ):

            print(
                f"Creating {label} rendition..."
            )


            rendition_started = (
                time.perf_counter()
            )


            hls_dir = (
                video_root /
                label
            )


            hls_dir.mkdir(
                parents=True,
                exist_ok=True
            )


            playlist_path = (
                hls_dir /
                "playlist.m3u8"
            )


            segment_pattern = (
                hls_dir /
                "segment%03d.ts"
            )


            command = [

                "ffmpeg",

                "-nostdin",

                "-y",

                "-i",
                str(input_path),

                "-vf",
                (
                    f"scale="
                    f"{settings['width']}:"
                    f"{settings['height']}"
                ),

                "-c:v",
                "libx264",

                "-preset",
                "veryfast",

                "-c:a",
                "aac",

                "-hls_time",
                "4",

                "-hls_playlist_type",
                "vod",

                "-hls_segment_filename",
                str(segment_pattern),

                str(playlist_path)
            ]


            result = subprocess.run(

                command,

                stdin=subprocess.DEVNULL,

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                text=True
            )


            rendition_seconds = (
                time.perf_counter()
                - rendition_started
            )


            metrics[
                "rendition_processing_seconds"
            ][label] = round(
                rendition_seconds,
                3
            )


            update_job(
                job_id,
                metrics=metrics
            )


            if result.returncode != 0:

                print(
                    f"{label} failed."
                )

                print(
                    result.stderr
                )


                raise RuntimeError(
                    f"Failed to create "
                    f"{label} rendition"
                )


            print(
                f"{label} completed in "
                f"{rendition_seconds:.3f}s."
            )


        # --------------------------------------------------
        # Create Master Playlist
        # --------------------------------------------------

        print(
            "Creating master playlist..."
        )


        master_playlist = (
            video_root /
            "master.m3u8"
        )


        with master_playlist.open(
            "w"
        ) as master:

            master.write(
                "#EXTM3U\n"
            )

            master.write(
                "#EXT-X-VERSION:3\n"
            )


            for label, settings in (
                renditions.items()
            ):

                master.write(

                    "#EXT-X-STREAM-INF:"

                    f"BANDWIDTH="
                    f"{settings['bandwidth']},"

                    f"RESOLUTION="
                    f"{settings['resolution']}\n"
                )


                master.write(
                    f"{label}/playlist.m3u8\n"
                )


        # --------------------------------------------------
        # Final Metrics
        # --------------------------------------------------

        total_processing_seconds = (
            time.perf_counter()
            - processing_started
        )


        metrics[
            "total_processing_seconds"
        ] = round(
            total_processing_seconds,
            3
        )


        # --------------------------------------------------
        # Complete Job
        # --------------------------------------------------

        update_job(

            job_id,

            status="completed",

            completed_at=utc_now_iso(),

            stream_url=(
                f"/stream/"
                f"{video_id}/"
                f"master.m3u8"
            ),

            renditions=list(
                renditions.keys()
            ),

            metrics=metrics,

            error=None
        )


        print(
            "Creating master playlist completed."
        )


        print(
            "Total processing time: "
            f"{total_processing_seconds:.3f}s"
        )


        print(
            "Worker job completed successfully."
        )


        print(
            "------------------------------\n"
        )


    except Exception as error:

        total_processing_seconds = (
            time.perf_counter()
            - processing_started
        )


        metrics[
            "total_processing_seconds"
        ] = round(
            total_processing_seconds,
            3
        )


        update_job(

            job_id,

            status="failed",

            completed_at=utc_now_iso(),

            metrics=metrics,

            error=str(error)
        )


        print(
            f"Worker job failed: {error}"
        )


        # Required so RQ can retry the job
        raise