from dataclasses import dataclass

@dataclass
class User:
    username: str
    salt: str
    vault_hash: str