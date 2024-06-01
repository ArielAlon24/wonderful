import requests
import time
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from pathlib import Path

STATUS_CODE_PENDING = 102
STATUS_CODE_FAILURE = 500
STATUS_CODE_NOT_FOUND = 404

CHUNK_SIZE = 1024 * 1024
TIMEOUT = 10
JOBS = 2


def upload(path: Path) -> Dict[str, Any]:
    with open(path, "rb") as file:
        response = requests.post("http://127.0.0.1:8000/upload", files={"file": file})

    return response.json()


def download(uuid: str, path: Path):
    while True:
        with requests.get(f"http://127.0.0.1:8000/result/{uuid}", stream=True) as r:
            if r.status_code == STATUS_CODE_PENDING:
                time.sleep(TIMEOUT)
                continue
            elif (
                r.status_code == STATUS_CODE_FAILURE
                or r.status_code == STATUS_CODE_NOT_FOUND
            ):
                r.raise_for_status()

            with open(path, "w", encoding="utf-8") as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk.decode("utf-8"))

            return


def transcribe(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} is not found.")
    json = upload(path)
    print(f"Uploaded: {path}")
    download(json["uuid"], path.with_suffix(".srt"))
    print(f"Downloaded: {path}")


def main() -> None:
    # simulating JOBS simultanious clients
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(transcribe, Path("mp3s/kaps-showcase-60s.mp3"))
            for _ in range(JOBS)
        ]

        for future in as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
