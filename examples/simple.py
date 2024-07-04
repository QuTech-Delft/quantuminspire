#!/usr/bin/env python

import time

from opensquirrel.ir import Bit, Qubit

from quantuminspire.sdk.models.circuit import Circuit
from quantuminspire.util.api.remote_backend import RemoteBackend

if __name__ == "__main__":

    with Circuit(platform_name="spin-2", program_name="prgm1", number_of_qubits=2) as c:
        c.ir.X(Qubit(0))
        c.ir.H(Qubit(1))
        c.ir.measure(Qubit(0), Bit(0))
        c.ir.measure(Qubit(1), Bit(1))

    backend = RemoteBackend()

    startTime = time.time()
    job_id = backend.run(c, backend_type_id=3, number_of_shots=1024)
    executionTime = time.time() - startTime
    print(f"Execution time in seconds: {executionTime}")
    print(f"job_id: {job_id}")
