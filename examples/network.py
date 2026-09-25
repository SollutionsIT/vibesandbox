import errno
import socket

assert {name for _, name in socket.if_nameindex()} == {"lo"}

try:
    socket.create_connection(("192.0.2.1", 80), timeout=0.5)
except OSError as error:
    assert error.errno == errno.ENETUNREACH
    print("Network connection unavailable")
else:
    raise RuntimeError("Unexpected network connection")
