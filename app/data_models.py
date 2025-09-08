import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

class TaskStatus(Enum):
    PENDING = "Pending"
    DONE = "Done"
    QUESTION = "Question"

class TaskPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

@dataclass
class Comment:
    text: str
    author: str # Could be member_id or name
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {"text": self.text, "author": self.author, "timestamp": self.timestamp.isoformat()}

    @classmethod
    def from_dict(cls, data):
        return cls(text=data["text"], author=data["author"], timestamp=datetime.fromisoformat(data["timestamp"]))

@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    comments: List[Comment] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    start_at: Optional[datetime] = None
    due_at: Optional[datetime] = field(default=None) # New field for due time
    assigned_to: Optional[str] = None # TaskList ID

@dataclass
class TaskList:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""