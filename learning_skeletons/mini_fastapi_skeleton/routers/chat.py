from schemas import ChatRequest
from services.chat_service import answer_question


def chat(request: ChatRequest) -> dict:
    return {"question": request.question, "answer": answer_question(request.question)}
