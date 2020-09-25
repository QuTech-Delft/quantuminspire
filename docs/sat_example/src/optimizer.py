from src.sat_utilities import alternative_and

optimizations = {
    "HXH": "Z",
    "HH": "",
    "XX": "",
    "ZX": "Y"
}
largest_opt = 3

forbidden = [
    ".grover_loop",
    "Toffoli",
    "CNOT",
    "CR"
]


def apply_optimizations(qasm, qubit_count, data_qubits):
    """
    Apply 3 types of optimization to the given QASM code:
        Combine groups of gates, such as H-X-H, to faster equivalent gates, Z in this case.
        Shift gates to be executed in parallel.
        Clean QASM code itself (q[1,2,3] becomes q[1:3])

    Args:
        qasm: Valid QASM code to optimize
        qubit_count: The total number of qubits
        data_qubits: The number of qubits that are not ancillaries

    Returns: A equivalent piece of QASM with optimizations applied
    """

    # run "speed" mode until QASM does not change
    prev_qasm = ""
    while prev_qasm != qasm:
        prev_qasm = qasm[:]
        qasm = optimize(qasm, qubit_count, data_qubits, mode="speed")

    # run "style" mode until QASM does not change
    prev_qasm = ""
    while prev_qasm != qasm:
        prev_qasm = qasm[:]
        qasm = optimize(qasm, qubit_count, data_qubits, mode="style")

    prev_qasm = ""
    while prev_qasm != qasm:
        prev_qasm = qasm[:]
        qasm = optimize_toffoli(qasm)

    # tidy up "ugly" optimized code
    qasm = clean_code(qasm)

    return qasm


def remove_gate_from_line(local_qasm_line, gate_symbol, qubit_index):
    """
    Removes the application of a specific gate on a specific qubit.

    Args:
        local_qasm_line: The line from which this call should be removed.
        gate_symbol: The symbol representing the gate
        qubit_index: The index of the target qubit

    Returns: The same line of QASM, with the gate removed.
    """

    # if gate applied to single qubit, remove gate call entirely
    single_application = "{} q[{}]".format(gate_symbol, qubit_index)
    if single_application in local_qasm_line:
        # if there is a parallel bar right
        local_qasm_line = local_qasm_line.replace(single_application + " | ", "")
        # else: if there is a parallel bar left
        local_qasm_line = local_qasm_line.replace(" | " + single_application, "")
        # else: if it is the only gate in parallelized brackets
        local_qasm_line = local_qasm_line.replace("{" + single_application + "}", "")
        # else: if it is not parellelized at all
        local_qasm_line = local_qasm_line.replace(single_application, "")

    # else remove just the number
    else:
        local_qasm_line = local_qasm_line.replace(",{},".format(qubit_index), ",")
        local_qasm_line = local_qasm_line.replace("[{},".format(qubit_index), "[")
        local_qasm_line = local_qasm_line.replace(",{}]".format(qubit_index), "]")

    return local_qasm_line


def add_gate_to_line(local_qasm_line, gate_symbol, qubit_index):
    """
    Add in parallel the application of a gate on a qubit.
    Args:
        local_qasm_line: The existing line of QASM to add the gate in.
        gate_symbol: The symbol representing the gate.
        qubit_index: The index of the target qubit.

    Returns: The same line of QASM with the gate added.
    """

    # if another operation is already called on this qubit, we have to put the new gate on a new line
    if "[" + str(qubit_index) + "]" in local_qasm_line \
            or "[" + str(qubit_index) + "," in local_qasm_line \
            or "," + str(qubit_index) + "," in local_qasm_line \
            or "," + str(qubit_index) + "]" in local_qasm_line:
        local_qasm_line += "\n{} q[{}]\n".format(gate_symbol, qubit_index)

    # if the line is not empty, we need to consider what's already present
    elif local_qasm_line != "":
        # a bracket indicates this line is parallelized with the { gate | gate | gate } syntax
        if "{" in local_qasm_line:
            # remove } from the line and add it back at the end
            local_qasm_line = local_qasm_line.rstrip("}| \n") + \
                              " | " + \
                              "{} q[{}]".format(gate_symbol, qubit_index) + \
                              "}\n"

        # no bracket means we have to add the parallelization syntax ourselves
        else:
            local_qasm_line = "{" + local_qasm_line.rstrip("\n") + \
                              " | " + \
                              "{} q[{}]".format(gate_symbol, qubit_index) + "}\n"

    # else, if the line IS empty, we can just put this gate in directly
    else:
        local_qasm_line = "{} q[{}]\n".format(gate_symbol, qubit_index)
    return local_qasm_line


def remove_toffoli_from_line(local_qasm_line, qubit_1, qubit_2, target_qubit):
    """
    Remove a specific Toffoli gate from a line of qasm.

    Args:
        local_qasm_line: The line of qasm
        qubit_1: The first control qubit of the Toffoli gate
        qubit_2: The second control qubit
        target_qubit: The target qubit

    Returns: The same line of qasm without the Toffoli gate call

    """
    single_application = "Toffoli q[{}],q[{}],q[{}]".format(qubit_1, qubit_2, target_qubit)

    # if there is a parallel bar right
    local_qasm_line = local_qasm_line.replace(single_application + " | ", "")
    # else: if there is a parallel bar left
    local_qasm_line = local_qasm_line.replace(" | " + single_application, "")
    # else: if it is the only gate in parallelized brackets
    local_qasm_line = local_qasm_line.replace("{" + single_application + "}", "")
    # else: if it is not parellelized at all
    local_qasm_line = local_qasm_line.replace(single_application, "")
    return local_qasm_line


def add_toffoli_to_line(local_qasm_line, qubit_1, qubit_2, target_qubit):
    """
    Add a single Toffoli gate application to the given line of qasm.

    Args:
        local_qasm_line: The line of qasm
        qubit_1: The first control qubit
        qubit_2: The second control qubit
        target_qubit: The target qubit

    Returns: The same line of qasm with the Toffoli gate added in parallel
    """

    single_application = "Toffoli q[{}],q[{}],q[{}]".format(qubit_1, qubit_2, target_qubit)

    # if the line is not empty, we need to consider what's already present
    if local_qasm_line != "":
        # a bracket indicates this line is parallelized with the { gate_1 | gate_2 | gate_3 } syntax
        if "{" in local_qasm_line:
            # remove } from the line and add it back at the end
            local_qasm_line = local_qasm_line.rstrip("}| \n") + \
                              " | " + \
                              single_application + \
                              "}\n"

        # no bracket means we have to add the parallelization syntax ourselves
        else:
            local_qasm_line = "{" + local_qasm_line.rstrip("\n") + \
                              " | " + \
                              single_application + "}\n"

    # else, if the line IS empty, we can just put this gate in directly
    else:
        local_qasm_line = single_application + "\n"
    return local_qasm_line


def optimize(qasm, qubit_count, data_qubits, mode="speed"):
    """
    Apply a single pass of performance-oriented optimizations to the given QASM.

    Args:
        qasm: A valid QASM program to optimize.
        qubit_count: The total number of qubits
        data_qubits: The number of qubits that are not ancillaries
        mode: Setting that determines the type of optimization:
            "speed" -> combine gates into equivalent smaller gates
            "style" -> parallelize gates for speedup and aesthetics

    Returns: Functionally the same QASM code, with one run of optimizations applied.
    """

    qasm_lines = qasm.split("\n")
    gates_applied = []
    for i in range(qubit_count):
        gates_applied.append([])

    for qasm_line_index in range(len(qasm_lines)):
        line = qasm_lines[qasm_line_index]
        if len(line) == 0:
            continue

        gate = line.split()[0].lstrip("{")
        if gate not in ["H", "X", "Y", "Z"]:
            gate = "_"

        if ":" in line:
            raise ValueError("Optimizer does not work well with q[0:3] notation!\n"
                             "Line: {}".format(line))

        if "[" in line:
            for element in line.split(" | "):
                gate = element.split()[0].lstrip("{")
                if gate not in ["H", "X", "Y", "Z"]:
                    gate = "_"

                alt_affected_qubits = []
                for possibly_affected in range(qubit_count):
                    hits = [
                        ",{},".format(possibly_affected),
                        "[{},".format(possibly_affected),
                        ",{}]".format(possibly_affected),
                        "[{}]".format(possibly_affected)
                    ]
                    if any(h in element for h in hits):
                        alt_affected_qubits.append(possibly_affected)

                for a in alt_affected_qubits:
                    gates_applied[a].append((qasm_line_index, gate))
        else:
            for a in range(data_qubits):
                gates_applied[a].append((qasm_line_index, gate))

    for qubit_index in range(len(gates_applied)):
        gates = gates_applied[qubit_index]
        skip_counter = 0
        for gate_index in range(len(gates)):
            if skip_counter > 0:
                skip_counter -= 1
                continue

            if mode == "speed":
                for offset in range(0, largest_opt - 1):
                    next_gates = "".join(map(lambda _: _[1], gates[gate_index:gate_index + largest_opt - offset]))
                    if next_gates in optimizations:
                        replacement = optimizations[next_gates]

                        line_indices = list(map(lambda _: _[0], gates[gate_index:gate_index + largest_opt - offset]))
                        # first, remove all gates that are to be replaced
                        for idx, line_number in enumerate(line_indices):
                            qasm_lines[line_number] = remove_gate_from_line(qasm_lines[line_number],
                                                                            next_gates[idx],
                                                                            qubit_index)

                        # add replacement gate to first line index
                        # unless there is no replacement gate, of course
                        if replacement != "":
                            qasm_lines[line_indices[0]] = add_gate_to_line(qasm_lines[line_indices[0]],
                                                                           replacement,
                                                                           qubit_index)

                        # ensure we skip a few gates
                        skip_counter += len(next_gates)

            elif mode == "style":
                # check if we can shift left to align with other gates
                current_line, current_gate = gates[gate_index]
                prev_line = current_line - 1

                if any(f in qasm_lines[current_line] or f in qasm_lines[prev_line] for f in forbidden):
                    continue
                # if this or the previous line has a break statement, no shifting possible
                if current_gate == "_" or (gates[gate_index - 1][1] == "_" and gates[gate_index - 1][0] == prev_line):
                    continue

                if qasm_lines[prev_line] == "":
                    continue

                # having passed these checks, we can try to actually shift
                if current_gate in ["H", "X", "Y", "Z"] and str(qubit_index) not in qasm_lines[prev_line]:
                    # remove from current line
                    qasm_lines[current_line] = remove_gate_from_line(qasm_lines[current_line], current_gate,
                                                                     qubit_index)
                    # add to left
                    qasm_lines[prev_line] = add_gate_to_line(qasm_lines[prev_line], current_gate, qubit_index)

    # remove blank lines
    qasm_lines = list(filter(lambda x: x not in ["", "{}", " "], qasm_lines))
    return "\n".join(qasm_lines).replace("\n\n", "\n")


def optimize_toffoli(qasm):
    """
    Specific style optimizer capable of left-shifting and annihilating Toffoli gates.

    Args:
        qasm: QASM to optimize

    Returns: Equivalent QASM with Toffoli gates optimized.
    """

    qasm_lines = qasm.split("\n")
    for current_line_index in range(1, len(qasm_lines)):
        cur_line = qasm_lines[current_line_index]
        prev_line = qasm_lines[current_line_index - 1]
        if "Toffoli" in cur_line and "Toffoli" in prev_line and ".grover_loop" not in prev_line:
            # find all Toffoli triplets in both lines
            prev_line_gates = prev_line.strip("{} |").split(" | ")
            prev_line_toffolis = list(filter(lambda x: "Toffoli" in x, prev_line_gates))

            cur_line_gates = cur_line.strip("{} |").split(" | ")
            cur_line_toffolis = list(filter(lambda x: "Toffoli" in x, cur_line_gates))

            any_updated = False
            for c_t in cur_line_toffolis:
                if any_updated:
                    break

                c_qubit_1, c_qubit_2, c_target_qubit = tuple(map(int, c_t.strip("Toffoli q[]").split("],q[")))
                shiftable = True

                for p_t in prev_line_toffolis:
                    p_qubit_1, p_qubit_2, p_target_qubit = tuple(map(int, p_t.strip("Toffoli q[]").split("],q[")))

                    if {c_qubit_1, c_qubit_2} == {p_qubit_1, p_qubit_2} and c_target_qubit == p_target_qubit:
                        # remove toffolis from both lines
                        cur_line = remove_toffoli_from_line(cur_line, c_qubit_1, c_qubit_2, c_target_qubit)
                        prev_line = remove_toffoli_from_line(prev_line, p_qubit_1, p_qubit_2, p_target_qubit)
                        shiftable = False
                        any_updated = True
                        break
                    elif len({c_qubit_1, c_qubit_2, c_target_qubit}.intersection(
                            {p_qubit_1, p_qubit_2, p_target_qubit})) != 0:
                        shiftable = False
                        break

                # check if anything has blocked us from shifting left
                if shiftable:
                    # otherwise we can go!
                    cur_line = remove_toffoli_from_line(cur_line, c_qubit_1, c_qubit_2, c_target_qubit)
                    prev_line = add_toffoli_to_line(prev_line, c_qubit_1, c_qubit_2, c_target_qubit)

                    any_updated = True

            if any_updated:
                qasm_lines[current_line_index] = cur_line
                qasm_lines[current_line_index - 1] = prev_line

    # remove blank lines
    qasm_lines = list(filter(lambda x: x not in ["", "{}", " "], qasm_lines))

    return "\n".join(qasm_lines).replace("\n\n", "\n")


def replace_toffoli_with_alt(qasm):
    """
    Replace all Toffoli gates (including parallelized ones) by their alternative representation.
    See src.grover.search_utilies.alternative_toffoli for more details.

    Args:
        qasm: The full qasm program that contains Toffoli gates to replace

    Returns: The same qasm with Toffoli gates replaced.
    """
    qasm_lines = qasm.split("\n")
    for current_line_index in range(len(qasm_lines)):
        cur_line = qasm_lines[current_line_index]
        if "Toffoli" in cur_line:
            # find all Toffoli triplets in this line

            cur_line_gates = cur_line.strip("{} |").split(" | ")
            cur_line_toffolis = list(filter(lambda x: "Toffoli" in x, cur_line_gates))

            multiple = len(cur_line_toffolis) > 1

            line_strings = []
            for i in range(7):
                if multiple:
                    line_strings.append("{")
                else:
                    line_strings.append("")

            for current_t in cur_line_toffolis:
                qubit_1, qubit_2, target_qubit = tuple(map(int, current_t.strip("Toffoli q[]").split("],q[")))
                alt_qasm_lines = alternative_and(qubit_1, qubit_2, target_qubit).split("\n")
                for j in range(7):
                    line_strings[j] += alt_qasm_lines[j]
                    if multiple:
                        line_strings[j] += " | "

            if multiple:
                for i in range(7):
                    line_strings[i] = line_strings[i][:-3] + "}"

            cur_line = "\n".join(line_strings)

            qasm_lines[current_line_index] = cur_line

    # remove blank lines
    qasm_lines = list(filter(lambda x: x not in ["", "{}", " "], qasm_lines))
    return "\n".join(qasm_lines).replace("\n\n", "\n")


def clean_code(qasm):
    """
    Clean given QASM by rewriting each line to a more readable format.
    For example, "{ X q[0] | H q[3,4,5] | X q[1] | X q[2] }"
    Would become "{ X q[0:2] | H q[3:5]"

    Args:
        qasm: Valid QASM code to clean

    Returns: The same QASM code with improved formatting.
    """

    qasm_lines = qasm.split("\n")
    for idx in range(len(qasm_lines)):
        line = qasm_lines[idx]
        gate_dict = {}
        new_line = ""
        if "Toffoli" not in line and "CR" not in line and "CNOT" not in line and ("{" in line or "," in line):
            line = line.strip("{}")
            elements = line.split("|")
            for e in elements:
                gate, target = e.split()
                indices = list(map(int, target.strip("q[]").split(",")))
                if gate not in gate_dict:
                    gate_dict[gate] = indices
                else:
                    gate_dict[gate] += indices

            parallel = len(gate_dict.keys()) > 1
            if parallel:
                new_line += "{ "
            for gate, indices in gate_dict.items():
                if max(indices) - min(indices) + 1 == len(indices) > 1:
                    new_line += "{} q[{}:{}]".format(gate, min(indices), max(indices))
                else:
                    new_line += "{} q[{}]".format(gate, ",".join(map(str, indices)))
                new_line += " | "

            new_line = new_line[:-3]
            if parallel:
                new_line += " }"
        else:
            new_line = line

        qasm_lines[idx] = new_line

    return "\n".join(qasm_lines)


