import requests
import time
import statistics
from pathlib import Path


API_BASE_URL = "http://127.0.0.1:8000"

TEST_VIDEO = Path("uploads/test-video.mp4")

RUNS = 5


def upload_video(video_path: Path):
    with video_path.open("rb") as video_file:
        response = requests.post(
            f"{API_BASE_URL}/upload",
            files={
                "file": (
                    video_path.name,
                    video_file,
                    "video/mp4"
                )
            }
        )

    response.raise_for_status()

    return response.json()


def wait_for_job(job_id: str):
    while True:
        response = requests.get(
            f"{API_BASE_URL}/jobs/{job_id}"
        )

        response.raise_for_status()

        job = response.json()

        status = job.get("status")

        if status == "completed":
            return job

        if status == "failed":
            raise RuntimeError(
                f"Job failed: {job.get('error')}"
            )

        time.sleep(0.5)


def main():
    if not TEST_VIDEO.exists():
        print(
            f"\nTest video not found: {TEST_VIDEO}"
        )

        print(
            "\nCopy a short MP4 into:"
        )

        print(
            "backend/uploads/test-video.mp4"
        )

        return


    queue_times = []
    processing_times = []
    end_to_end_times = []


    print("\n==============================")
    print("STREAMFORGE BENCHMARK")
    print("==============================")

    print(
        f"Runs: {RUNS}"
    )

    print(
        f"Video: {TEST_VIDEO}"
    )

    print("==============================\n")


    for run_number in range(
        1,
        RUNS + 1
    ):

        print(
            f"Run {run_number}/{RUNS}"
        )


        benchmark_started = (
            time.perf_counter()
        )


        upload_result = upload_video(
            TEST_VIDEO
        )


        job_id = upload_result[
            "job_id"
        ]


        print(
            f"Job ID: {job_id}"
        )


        job = wait_for_job(
            job_id
        )


        end_to_end_seconds = (
            time.perf_counter()
            - benchmark_started
        )


        metrics = job.get(
            "metrics",
            {}
        )


        queue_wait = metrics.get(
            "queue_wait_seconds"
        )


        processing_time = metrics.get(
            "total_processing_seconds"
        )


        if queue_wait is not None:
            queue_times.append(
                queue_wait
            )


        if processing_time is not None:
            processing_times.append(
                processing_time
            )


        end_to_end_times.append(
            end_to_end_seconds
        )


        print(
            f"Queue wait: "
            f"{queue_wait:.3f}s"
            if queue_wait is not None
            else "Queue wait: N/A"
        )


        print(
            f"Processing: "
            f"{processing_time:.3f}s"
            if processing_time is not None
            else "Processing: N/A"
        )


        print(
            f"End-to-end: "
            f"{end_to_end_seconds:.3f}s"
        )


        rendition_metrics = metrics.get(
            "rendition_processing_seconds",
            {}
        )


        for label, seconds in (
            rendition_metrics.items()
        ):

            print(
                f"{label}: "
                f"{seconds:.3f}s"
            )


        print()


    print("==============================")
    print("BENCHMARK RESULTS")
    print("==============================")


    if queue_times:

        print(
            f"Average queue wait: "
            f"{statistics.mean(queue_times):.3f}s"
        )

        print(
            f"Fastest queue wait: "
            f"{min(queue_times):.3f}s"
        )

        print(
            f"Slowest queue wait: "
            f"{max(queue_times):.3f}s"
        )


    if processing_times:

        print()

        print(
            f"Average processing: "
            f"{statistics.mean(processing_times):.3f}s"
        )

        print(
            f"Fastest processing: "
            f"{min(processing_times):.3f}s"
        )

        print(
            f"Slowest processing: "
            f"{max(processing_times):.3f}s"
        )


    if end_to_end_times:

        print()

        print(
            f"Average end-to-end: "
            f"{statistics.mean(end_to_end_times):.3f}s"
        )

        print(
            f"Fastest end-to-end: "
            f"{min(end_to_end_times):.3f}s"
        )

        print(
            f"Slowest end-to-end: "
            f"{max(end_to_end_times):.3f}s"
        )


    print("==============================\n")


if __name__ == "__main__":
    main()