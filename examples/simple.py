#!/usr/bin/env python

import time

from quantuminspire.sdk.models.circuit import Circuit
from quantuminspire.util.api.remote_backend import RemoteBackend

if __name__ == "__main__":

    with Circuit(platform_name="spin-2", program_name="prgm1") as c:
        k = c.init_kernel("new_kernel", 2)
        k.x(0)
        k.hadamard(1)
        k.measure(0)
        k.measure(1)

    backend = RemoteBackend()

    startTime = time.time()
    job_id = backend.run(c, backend_type_id=3, number_of_shots=1024)
    executionTime = time.time() - startTime
    print(f"Execution time in seconds: {executionTime}")
    print(f"job_id: {job_id}")
