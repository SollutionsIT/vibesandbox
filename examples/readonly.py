import errno

try:
    with open("/vibesandbox-probe", "w") as probe:
        probe.write("safe probe")
except OSError as error:
    assert error.errno == errno.EROFS
    print("Root filesystem write denied")
else:
    raise RuntimeError("Unexpected writable root")
