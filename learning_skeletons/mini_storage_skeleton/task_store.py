class MiniTaskStore:
    def __init__(self) -> None:
        self.tasks = []
        self.next_id = 1

    def enqueue(self, payload: dict) -> dict:
        task = {"id": self.next_id, "payload": payload, "status": "NEW"}
        self.next_id += 1
        self.tasks.append(task)
        return task

    def claim(self) -> dict | None:
        for task in self.tasks:
            if task["status"] == "NEW":
                task["status"] = "PROCESSING"
                return task
        return None

    def mark_done(self, task_id: int) -> dict | None:
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = "DONE"
                return task
        return None
