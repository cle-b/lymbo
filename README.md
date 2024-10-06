# lymbo

* **lymbo** is a test runner designed for large test suites and small scripts.

The key features of **lymbo** are:

  * Parallel execution by default
  * Simplicity
  * No dependencies


## Concetps

In **lymbo**, there are only two key concepts to understand: `test` and `resource`.

### Test

To define a test, simply decorate a function or a method using `lymbo.test()`:

```python
import lymbo

@lymbo.test()
def addition():
    assert 1 + 2 == 3, "Addition test failed: 1 + 2 did not equal 3"
```

You can run the test using the command `lymbo`:

```
(venv) ~/dev/lymbo$ lymbo examples/ 
** lymbo 0.2.0 (python 3.9.18) (Linux-5.15.0-122-generic-x86_64-with-glibc2.35) **
==== collecting tests
==== 1 test in 1 group
==== running tests
.P
==== tests executed in 0 second
==== results
- examples/readme.py::addition() [PASSED]
==== 1 passed 
```

A test is parameterizable:

```python
import math

import lymbo
from lymbo import args, expand

@lymbo.test(args(n=expand(1, 4, 9, 116)))
def is_perfect_square(n):
    assert int(math.sqrt(n)) ** 2 == n, f"Assertion failed: {n} is not a perfect square. Its square root is {math.sqrt(n)}."
```

You can run only these new tests using the `filter` option:

```
(venv) ~/dev/lymbo$ lymbo examples/ --filter=square
** lymbo 0.2.0 (python 3.9.18) (Linux-5.15.0-122-generic-x86_64-with-glibc2.35) **
==== collecting tests
==== 4 tests in 4 groups
==== running tests
.P.P.P.F
==== tests executed in 1 second
==== results
- examples/readme.py::is_perfect_square(n=1) [PASSED]
- examples/readme.py::is_perfect_square(n=4) [PASSED]
- examples/readme.py::is_perfect_square(n=9) [PASSED]
- examples/readme.py::is_perfect_square(n=116) [FAILED]
==== 3 passed 1 failed  
==== failures
examples/readme.py::is_perfect_square(n=116)
 - - - - reason:
  Assertion failed: 116 is not a perfect square. Its square root is 10.770329614269007.
  ---------------------
  AssertionError in /home/cle/dev/lymbo/examples/readme.py, line 14, in is_perfect_square:
      12: @lymbo.test(args(n=expand(1, 4, 9, 116)))
      13: def is_perfect_square(n):
  ==> 14:     assert (
      15:         int(math.sqrt(n)) ** 2 == n
      16:     ), f"Assertion failed: {n} is not a perfect square. Its square root is {math.sqrt(n)}."
====
```

In the example above, the tests were executed independently. As a result, they may have been run in parallel by multiple workers.

We can group the tests to ensure they run sequentially on the same worker. In the example below, we will group the tests by function and execute a test collection to print the test plan:

```
(venv) ~/dev/lymbo$ lymbo examples/ --groupby=function --collect
** lymbo 0.2.0 (python 3.9.18) (Linux-5.15.0-122-generic-x86_64-with-glibc2.35) **
==== collecting tests
- examples/readme.py::addition()
+ 4 tests grouped by examples/readme.py::None::is_perfect_square
  | - examples/readme.py::is_perfect_square(n=1)
  | - examples/readme.py::is_perfect_square(n=4)
  | - examples/readme.py::is_perfect_square(n=9)
  | - examples/readme.py::is_perfect_square(n=116)
==== 5 tests in 2 groups
``` 

For a very simple unit test, you can decorate the function you want to test and verify the returned value to assert the test outcome.

```python
@lymbo.test(args(a=4, b=2), expected(2))
@lymbo.test(args(a=9, b=2), expected=expected(4.5))
@lymbo.test(args(a=9, b=0), expected=expected(ZeroDivisionError))
def division(a, b):
    return a / b
```

```
(venv) ~/dev/lymbo$ lymbo examples/readme.py --filter=division
** lymbo 0.3.0 (python 3.9.18) (Linux-5.15.0-122-generic-x86_64-with-glibc2.35) **
==== collecting tests
==== 3 tests in 3 groups
==== running tests
.P.P.P
==== tests executed in 0 second
==== results
- examples/readme.py::division(a=4,b=2)->(value=2) [PASSED]
- examples/readme.py::division(a=9,b=2)->(value=4.5) [PASSED]
- examples/readme.py::division(a=9,b=0)->(value=ZeroDivisionError) [PASSED]
==== 3 passed 
```

### Resource

A resource is a standard context manager.

In the example below, we will execute 3 tests using 2 workers. Each test will use a resource that takes 5 seconds.

```python
import contextlib
import time

import lymbo


@contextlib.contextmanager
def wait_five_seconds():
    time.sleep(5)
    yield


@lymbo.test()
def demo_resource_no_scope_first_test():
    with wait_five_seconds():
        assert True


@lymbo.test()
def demo_resource_no_scope_second_test():
    with wait_five_seconds():
        assert True


@lymbo.test()
def demo_resource_no_scope_third_test():
    with wait_five_seconds():
        assert True
```

The tests will be executed in 10 seconds because the resource (which takes 5 seconds) is not shared between tests.

```
(venv) ~/dev/lymbo$ lymbo examples/ --filter=resource_no_scope --workers=2
** lymbo 0.2.0 (python 3.9.18) (Linux-5.15.0-122-generic-x86_64-with-glibc2.35) **
==== collecting tests
==== 3 tests in 3 groups
==== running tests
..PP.P
==== tests executed in 10 seconds
==== results
- examples/readme.py::demo_resource_no_scope_first_test() [PASSED]
- examples/readme.py::demo_resource_no_scope_second_test() [PASSED]
- examples/readme.py::demo_resource_no_scope_third_test() [PASSED]
==== 3 passed
```

You can share a resource between different tests, regardless of the worker on which they are executed, by using a specific scope.

In the example below, a resource will be shared at the global scope, meaning all tests can access it, no matter the module, class, or function in which the test is defined.

```python
import contextlib
import time

import lymbo
from lymbo import scope_global


@contextlib.contextmanager
def wait_five_seconds():
    time.sleep(5)
    yield

@lymbo.test()
def demo_resource_scope_first_test():
    with scope_global(wait_five_seconds):
        assert True


@lymbo.test()
def demo_resource_scope_second_test():
    with scope_global(wait_five_seconds):
        assert True


@lymbo.test()
def demo_resource_scope_third_test():
    with scope_global(wait_five_seconds):
        assert True
```

In this case, the execution of the 3 tests using 2 workers will take only 5 seconds because the resource is created once and shared among all the tests.

```
(venv) ~/dev/lymbo$ lymbo examples/ --filter=resource_scope --workers=2
** lymbo 0.2.0 (python 3.9.18) (Linux-5.15.0-122-generic-x86_64-with-glibc2.35) **
==== collecting tests
==== 3 tests in 3 groups
==== running tests
..PP.P
==== tests executed in 5 seconds
==== results
- examples/readme.py::demo_resource_scope_first_test() [PASSED]
- examples/readme.py::demo_resource_scope_second_test() [PASSED]
- examples/readme.py::demo_resource_scope_third_test() [PASSED]
==== 3 passed  
```

## Command line

```
(venv) ~/dev/lymbo$ lymbo -h
usage: lymbo [-h] [--version] [--collect] [--groupby {GroupBy.NONE,GroupBy.MODULE,GroupBy.CLASS,GroupBy.FUNCTION}] [--report REPORT]
             [--log-level {LogLevel.NOTSET,LogLevel.DEBUG,LogLevel.INFO,LogLevel.WARNING,LogLevel.ERROR,LogLevel.CRITICAL}] [--log LOG]
             [--report-failure {ReportFailure.NONE,ReportFailure.SIMPLE,ReportFailure.NORMAL,ReportFailure.FULL}] [--workers WORKERS]
             [--filter FILTER]
             [PATH ...]

A test runner designed for large test suites and small scripts.

positional arguments:
  PATH                  Path(s) for test collection

optional arguments:
  -h, --help            show this help message and exit
  --version             Print the version and exit.
  --collect             Print the test plan and exit.
  --groupby {GroupBy.NONE,GroupBy.MODULE,GroupBy.CLASS,GroupBy.FUNCTION}
                        Grouped tests are executed sequentialy.
  --report REPORT       Save the report in that directory.
  --log-level {LogLevel.NOTSET,LogLevel.DEBUG,LogLevel.INFO,LogLevel.WARNING,LogLevel.ERROR,LogLevel.CRITICAL}
                        The log level
  --log LOG             Path to the log file.
  --report-failure {ReportFailure.NONE,ReportFailure.SIMPLE,ReportFailure.NORMAL,ReportFailure.FULL}
                        The level of detail to display in the console in case of a failure.
  --workers WORKERS     The number of workers in parrallel (default = number of CPU).
  --filter FILTER       Select only the tests that match this filter (include full path and parameters).
```