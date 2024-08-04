from lymbo.item import TestItem


def show_test_plan(
    test_plan: list[list[TestItem]], show_group: bool = False
) -> list[str]:
    output: list[str] = []
    for tests in test_plan:
        if len(tests) > 1:
            output.append(f"+ group of {len(tests)} tests")
        for test in tests:
            output.append(f"{' -' if len(tests)>1 else '-'} {test}")
    return output
