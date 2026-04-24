from tools.registry import build_default_registry


def main() -> None:
    registry = build_default_registry()

    print("Available tools:")
    for tool in registry.list_tools():
        print(tool)

    print("\nSearch tool result:")
    search_result = registry.execute(
        "search",
        {"query": "agent"},
    )
    print(search_result.model_dump())

    print("\nHTTP tool result:")
    http_result = registry.execute(
        "http_get",
        {"url": "https://httpbin.org/get"},
    )
    print(http_result.model_dump())


if __name__ == "__main__":
    main()