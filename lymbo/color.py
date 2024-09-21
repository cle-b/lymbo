import os

if os.name == "nt":
    RED = ""
    GREEN = ""
    YELLOW = ""
    RESET = ""
else:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
