from agent import MiniAgent
from tools.case_search_tool import case_search_tool
from tools.change_tool import change_tool
from tools.metric_tool import metric_tool


def main() -> None:
    agent = MiniAgent(
        tools={
            "metric_tool": metric_tool,
            "change_tool": change_tool,
            "case_search_tool": case_search_tool,
        }
    )
    result = agent.run({"service": "payment-api", "metric": "mysql.connections"})
    print(result)


if __name__ == "__main__":
    main()
