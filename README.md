# StreamForge

StreamForge is a video streaming backend that accepts uploaded videos, processes them with FFmpeg, converts them into HLS streaming segments, and serves the processed stream through a FastAPI backend.

The project is being built incrementally to explore the engineering concepts behind large-scale video streaming systems, including transcoding, adaptive bitrate streaming, caching, background workers, observability, and fault tolerance.

## Current MVP

The current MVP supports an end-to-end streaming pipeline:

```text
Upload Video
     ↓
FastAPI Backend
     ↓
Store Original Video
     ↓
FFmpeg Transcoding
     ↓
HLS Segmentation
     ↓
FastAPI Static Delivery
     ↓
Browser Video Playback
```

A user can upload a video through the StreamForge frontend, the backend processes the video into HLS format, and the resulting stream can be played directly in the browser.

## Features

* Video uploads through FastAPI
* FFmpeg-based video processing
* H.264 video encoding
* AAC audio encoding
* 720p video transcoding
* HLS video segmentation
* `.m3u8` playlist generation
* HTTP delivery of HLS playlists and segments
* Browser-based video playback
* Dynamic stream URL generation
* Simple upload-and-play frontend

## Tech Stack

* **Python**
* **FastAPI**
* **FFmpeg**
* **HLS**
* **HTML**
* **JavaScript**
* **Uvicorn**

## Project Structure

```text
streamforge/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── static/
│   │   └── index.html
│   ├── uploads/
│   └── processed/
├── .gitignore
└── README.md
```

The `uploads/` and `processed/` directories are ignored by Git because they contain local video files generated while running the application.

## How It Works

### 1. Video Upload

The frontend sends a selected video to the FastAPI `/upload` endpoint using a multipart HTTP request.

### 2. Video Processing

The backend stores the original upload and invokes FFmpeg using Python's `subprocess` module.

FFmpeg:

* reads the original video
* scales the video to 720p
* encodes video using H.264
* encodes audio using AAC
* converts the result into HLS

### 3. HLS Segmentation

Instead of serving one large video file, StreamForge divides the video into smaller streaming segments.

Example:

```text
processed/
└── video/
    └── 720p/
        ├── playlist.m3u8
        ├── segment000.ts
        ├── segment001.ts
        └── segment002.ts
```

The `.m3u8` playlist tells the video player which segments to request and in what order.

### 4. Streaming

FastAPI exposes the processed files through the `/stream` route.

After processing, the backend returns a stream URL such as:

```text
/stream/video/720p/playlist.m3u8
```

The frontend automatically loads this URL into the video player.

## Running Locally

### Clone the repository

```bash
git clone https://github.com/nowusu1/streamforge.git
cd streamforge/backend
```

### Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Install FFmpeg

On macOS with Homebrew:

```bash
brew install ffmpeg
```

Verify the installation:

```bash
ffmpeg -version
```

### Start StreamForge

```bash
uvicorn main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Open the application at:

```text
http://127.0.0.1:8000/app/
```

FastAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Current Architecture

```text
Browser
   |
   | POST /upload
   v
FastAPI
   |
   | Save uploaded file
   v
Local Storage
   |
   | Invoke FFmpeg
   v
Transcoding Pipeline
   |
   | Generate HLS playlist + segments
   v
Processed Storage
   |
   | GET /stream/...
   v
Browser Video Player
```

## Planned Development

StreamForge will continue evolving beyond the initial MVP.

Planned features include:

* 480p, 720p, and 1080p HLS renditions
* Adaptive bitrate streaming
* Automatic quality selection based on network conditions
* Background video-processing workers
* Asynchronous job queues
* Redis caching
* Retry and failure-recovery mechanisms
* Concurrent processing
* Video metadata extraction
* Persistent storage
* Metrics and observability
* Throughput and latency benchmarking
* Load testing
* Improved frontend experience
* Containerized deployment

## Engineering Goals

StreamForge is designed as a systems-focused project rather than a simple video-sharing interface.

The long-term goal is to explore problems such as:

* How should expensive video-processing jobs be handled asynchronously?
* How can repeated video requests avoid unnecessary origin reads?
* How should failed transcoding jobs be retried safely?
* How can video quality adapt to changing network bandwidth?
* How does the system behave under concurrent streaming workloads?
* How can latency, throughput, cache-hit ratio, and failure rates be measured?

## Status

**MVP v1: Complete**

Current pipeline:

```text
Upload → Transcode → Segment → Serve → Stream
```

Development of MVP v2 is in progress.
