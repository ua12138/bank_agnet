from state import Step


class MiniAgent:
    sequence = ["metric_tool", "change_tool", "case_search_tool"]

    def __init__(self, tools: dict[str, callable]) -> None:
        self.tools = tools

    def next_action(self, steps: list[Step]) -> str | None:
        done_actions = {step.action for step in steps}
        for name in self.sequence:
            if name not in done_actions:
                return name
        return None

    def run(self, incident: dict) -> dict:
        steps: list[Step] = []
        while True:
            tool_name = self.next_action(steps)
            if tool_name is None:
                break
            observation = self.tools[tool_name](incident)
            steps.append(Step(action=tool_name, observation=observation))
        return {
            "incident": incident,
            "steps": [step.__dict__ for step in steps],
            "final_answer": "Likely database pressure with recent change risk.",
        }
