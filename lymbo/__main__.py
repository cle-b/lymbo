import platform
import sys

import lymbo
from lymbo.collect import collect_tests
from lymbo.config import parse_args
from lymbo.run import run_test_plan
from lymbo.ui import show_test_plan


def lymbo_entry_point():

    config = parse_args()

    if config.version:
        print(lymbo.__version__)
        sys.exit(5)

    print(
        f"** lymbo {lymbo.__version__} (python {platform.python_version()}) ({platform.platform()}) **"
    )

    print("==== collecting tests")
    test_plan = collect_tests(config.paths, config.groupby)

    if config.collect:
        print("\n".join(show_test_plan(test_plan, config.groupby)))

    nb_tests, nb_groups = test_plan.count
    print(
        f"==== {nb_tests} test{'s' if nb_tests>1 else ''} in {nb_groups} group{'s' if nb_groups>1 else ''}"
    )

    if config.collect:
        sys.exit(5)

    run_test_plan(test_plan)


if __name__ == "__main__":
    lymbo_entry_point()
