import sys
for _ in range(1000):
 print('x'*1000)
 print('y'*1000, file=sys.stderr)
