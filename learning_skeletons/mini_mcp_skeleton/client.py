from server import handle_call


def main() -> None:
    payload = {"name": "search_manual", "arguments": {"query": "db saturation"}}
    print(handle_call(payload))


if __name__ == "__main__":
    main()
