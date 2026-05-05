from dataclasses import dataclass


@dataclass
class Step:
    action: str
    observation: dict
