from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from contextlib import asynccontextmanager
from whisper import utils, load_model
from asyncio import Queue
from uuid import uuid4
import asyncio
import aiofiles
import logging
import os

from typing import AsyncGenerator, Tuple

from .task import Task, TaskState
from .async_dict import AsyncDict


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
FILE_STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MB


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.debug(f"Initiated '{UPLOAD_DIR}' directory.")
    os.makedirs(RESULT_DIR, exist_ok=True)
    logger.debug(f"Initiated '{UPLOAD_DIR}' directory.")
    asyncio.create_task(task_consumer())
    logger.debug(f"Initiated task consumer.")
    yield


app = FastAPI(lifespan=lifespan)
model = load_model("base")

queue = Queue()
tasks: AsyncDict[str, Task] = AsyncDict()


def transcribe_process(task: Task) -> Tuple[str, TaskState]:
    try:
        result = model.transcribe(task.path)
        os.remove(task.path)

        writer = utils.WriteSRT(UPLOAD_DIR)
        with open(task.out_path(RESULT_DIR), "w") as file:
            writer.write_result(result, file)

        return (task.uuid, TaskState.SUCCESS)

    except Exception as e:
        logger.error(f"Could not complete {task}: {e}")
        return (task.uuid, TaskState.FAILURE)


async def task_consumer():
    while True:
        task = await queue.get()
        logger.debug(f"Task consumer started working on {task}")
        if not os.path.exists(task.path):
            raise HTTPException(status_code=500, detail="Internal Server Error")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, transcribe_process, task)
        uuid, state = result
        task.state = state

        queue.task_done()
        logger.debug(f"Task {uuid} completed with state {state}.")


@app.post("/upload")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    uuid = str(uuid4())
    path = os.path.join(UPLOAD_DIR, uuid)

    content = await file.read()
    async with aiofiles.open(path, "wb") as buffer:
        await buffer.write(content)

    task = Task(uuid=uuid, path=path)

    background_tasks.add_task(queue.put, task)
    background_tasks.add_task(tasks.set, uuid, task)

    return {"uuid": task.uuid}


@app.get("/result/{uuid}")
async def get_result(uuid: str):
    task = await tasks.get(uuid)
    if task is None:
        raise HTTPException(status_code=404, detail="Task Not Found")

    if task.state == TaskState.PENDING:
        raise HTTPException(status_code=102, detail=task.state.value)
    elif task.state == TaskState.FAILURE:
        await tasks.remove(task.uuid)
        os.remove(task.path)
        raise HTTPException(status_code=500, detail=task.state.value)
    elif task.state == TaskState.SUCCESS:
        await tasks.remove(task.uuid)

        if not os.path.exists(task.out_path(RESULT_DIR)):
            raise HTTPException(status_code=500, detail="Internal Server Error")

        return StreamingResponse(
            file_streamer(task.out_path(RESULT_DIR)),
            media_type="text/plain",
            background=BackgroundTask(os.remove, task.out_path(RESULT_DIR)),
        )
    else:
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def file_streamer(path: str) -> AsyncGenerator[str, None]:
    async with aiofiles.open(path, "r") as file:
        while True:
            chunk = await file.read(FILE_STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
