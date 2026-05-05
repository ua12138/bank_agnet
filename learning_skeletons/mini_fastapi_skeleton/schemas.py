from dataclasses import dataclass


@dataclass
class ChatRequest:
    question: str
