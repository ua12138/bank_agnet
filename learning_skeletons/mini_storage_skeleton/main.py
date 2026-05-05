from task_store import MiniTaskStore


def main() -> None:
    store = MiniTaskStore()
    task = store.enqueue({"incident_id": "inc_001"})
    print("after enqueue:", task)
    task = store.claim()
    print("after claim:", task)
    task = store.mark_done(task["id"])
    print("after done:", task)


if __name__ == "__main__":
    main()
