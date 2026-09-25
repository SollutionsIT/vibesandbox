"""Bounded probe: at most 48 sleeping children, always reaped."""

import subprocess
import sys

children = []
try:
    for _ in range(48):
        try:
            children.append(subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"]))
        except BlockingIOError:
            print("Process creation limited")
            break
    else:
        raise RuntimeError("Expected default PID policy to limit children")
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait()
