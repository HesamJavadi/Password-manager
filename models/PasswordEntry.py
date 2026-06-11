import uuid
from dataclasses import field, dataclass, asdict
from datetime import datetime


@dataclass
class PasswordEntry:
    title: str
    password: str
    username: str = ""
    url: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PasswordEntry":
        return cls(**data)

