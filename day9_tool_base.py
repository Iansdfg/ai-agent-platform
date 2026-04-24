from tools.registry import build_default_registry


def main() -> None:
    registry = build_default_registry()

    print("Available tools:")
    for tool_schema in registry.list_tools():
        print(tool_schema)

    print("\nExecute learning_notes tool:")
    result = registry.execute(
        "learning_notes",
        {"query": "agent orchestration"},
    )

    print(result.model_dump())


if __name__ == "__main__":
    main()