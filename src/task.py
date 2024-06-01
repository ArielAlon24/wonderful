from dataclasses import dataclass, field
from enum import Enum
import os


class TaskState(Enum):
    SUCCESS = "success"
    PENDING = "pending"
    FAILURE = "failure"


@dataclass
class Task:
    uuid: str
    path: str
    state: TaskState = field(default=TaskState.PENDING)

    def out_path(self, out_dir: str) -> str:
        return os.path.join(out_dir, f"{self.uuid}.srt")
