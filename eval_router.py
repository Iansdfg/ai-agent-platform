from router import QueryRouter


def main():
    router = QueryRouter()

    cases = [
        {
            "query": "What customers prefer premium dog food?",
            "expected": "rag",
        },
        {
            "query": "Create draft for a dog food campaign",
            "expected": "tool",
        },
        {
            "query": "Get draft 123",
            "expected": "tool",
        },
        {
            "query": "What is email marketing?",
            "expected": "direct",
        },
    ]

    correct = 0

    for case in cases:
        decision = router.route(case["query"])
        passed = decision.route == case["expected"]
        correct += int(passed)

        print({
            "query": case["query"],
            "expected": case["expected"],
            "actual": decision.route,
            "passed": passed,
            "reason": decision.reason,
        })

    print(f"Router accuracy: {correct}/{len(cases)} = {correct / len(cases):.2f}")


if __name__ == "__main__":
    main()