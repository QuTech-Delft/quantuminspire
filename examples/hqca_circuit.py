from typing import Dict, List, cast

from quantuminspire.sdk.circuit import Circuit


def execute(results: Dict[str, List[float]], shots_requested: int, shots_done: int) -> str:
    with Circuit(platform_name="spin-2", program_name="prgm1") as c:
        k = c.init_kernel("new_kernel", 2)
        k.hadamard(0)
        k.cnot(0, 1)

    return c.qasm
