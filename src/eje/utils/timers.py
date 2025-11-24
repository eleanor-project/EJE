import time
from contextlib import contextmanager


@contextmanager
def timed_section(label="block"):
    start = time.time()
    yield
    duration = time.time() - start
    print(f"{label} took {duration:.4f}s")
