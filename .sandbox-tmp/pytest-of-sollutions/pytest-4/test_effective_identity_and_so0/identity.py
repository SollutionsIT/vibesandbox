import os
assert os.getuid() == 65532
status = open('/proc/self/status').read()
assert 'NoNewPrivs:\t1' in status
assert 'CapEff:\t0000000000000000' in status
assert 'Seccomp:\t2' in status
try:
    open('/source/main.py', 'w')
except OSError:
    print('source read-only')
else:
    raise RuntimeError('source writable')
assert not os.path.exists('/var/run/docker.sock')
