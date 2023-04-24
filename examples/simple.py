#!/usr/bin/env python

import time

from quantuminspire.sdk.models.circuit import Circuit
from quantuminspire.util.api.remote_runtime import RemoteRuntime

with Circuit(platform_name="spin-2", program_name="prgm1") as c:
    k = c.init_kernel("new_kernel", 2)
    k.x(0)
    k.hadamard(1)
    k.measure(0)
    k.measure(1)

print(c.content)

runtime = RemoteRuntime()

startTime = time.time()
runtime.run(c)
executionTime = time.time() - startTime
print("Execution time in seconds: " + str(executionTime))
