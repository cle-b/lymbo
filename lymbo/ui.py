from lymbo.config import GroupBy
from lymbo.item import TestPlan


def show_test_plan(test_plan: TestPlan, group_by: GroupBy) -> list[str]:
    output: list[str] = []
    nb_tests = 0
    for tests in test_plan:
        if len(tests) > 1:
            group_msg = f"+ {len(tests)} tests grouped by "
            if group_by == GroupBy.MODULE:
                group_msg += f"{tests[0].path}"
            if group_by == GroupBy.CLASS:
                group_msg += f"{tests[0].path}::{tests[0].cls}"
            if group_by == GroupBy.FUNCTION:
                group_msg += f"{tests[0].path}::{tests[0].cls}::{tests[0].fnc}"
            output.append(group_msg)
        for test in tests:
            nb_tests += 1
            output.append(f"{'  | -' if len(tests)>1 else '-'} {test}")
    return output
