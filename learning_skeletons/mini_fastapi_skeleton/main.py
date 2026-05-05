from schemas import ChatRequest
from routers.chat import chat


def main() -> None:
    request = ChatRequest(question="what is task queue?")
    response = chat(request)
    print(response)


if __name__ == "__main__":
    main()
