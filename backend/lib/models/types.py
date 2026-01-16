import enum
from dataclasses import dataclass



class TaskStatus(enum.Enum):
    UP = 101
    CORRUPT = 102
    MUMBLE = 103
    DOWN = 104
    CHECK_FAILED = 110

    def __str__(self) -> str:
        return self.name


class Action(enum.Enum):
    CHECK = 0
    PUT = 1
    GET = 2

    def __str__(self) -> str:
        return self.name


@dataclass
class CheckerVerdict:
    status: TaskStatus
    action: Action
    public_message: str = ""
    private_message: str = ""
    command: str = ""
    
    def __str__(self) -> str:
        return f"CheckerVerdict(status={self.status}, action={self.action})"