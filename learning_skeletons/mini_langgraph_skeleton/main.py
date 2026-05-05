from graph import run_graph


def main() -> None:
    state = {"duplicate": False, "approved": True, "history": []}
    final_state = run_graph(state)
    print(final_state)


if __name__ == "__main__":
    main()
