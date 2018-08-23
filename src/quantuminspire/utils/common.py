import itertools
import logging
import warnings

import numpy as np
import qiskit
from IPython.display import Latex, Math, display
from qiskit import QuantumCircuit

logger = logging.getLogger(__name__)


def format_vector(state_vector, verbose=0):
    """ Format a state vector in LaTeX format

    Args:
        state_vector (array): state vector
    Returns:
        s (str): state vector in LaTeX format
    """
    s = ''
    n = int(np.log2(len(state_vector)))
    xx = list(itertools.product(*([0, 1],) * n))
    if verbose:
        print(xx)
    states = [''.join([str(p) for p in x]) for x in xx]
    if verbose:
        print(states)
    for ii, v in enumerate(state_vector):
        st = states[ii]
        a, b = float(np.real(v)), float(np.imag(v))

        def fmt(v, single=False):
            if np.abs(v - 1) < 1e-8:
                return ''
            if single and np.abs(v + 1) < 1e-8:
                return '-'
            return '%.2g' % v

        # print('%s %s' % (a,fmt(a)) )
        if np.abs(b) > 1e-8:
            if ii > 0:
                if len(s) > 0:
                    s += ' + '
            s += r'(%s + %s j) \left\lvert %s\right\rangle' % (fmt(a), fmt(b), st)
        else:
            if np.abs(a) > 1e-8:
                if ii > 0 and len(s) > 0 and a > 0:
                    s += ' + '
                s += r'%s \left\lvert %s\right\rangle' % (fmt(a, True), st)
            else:
                pass
    return s


def run_circuit(qc, q, n=None, verbose=0, backend='local_statevector_simulator'):
    """ Run a circuit on all input vectors and show the output

    Args:
        qc (quantum circuit):
        q (QuantumRegister)
        n (int or None): number of qubits
    """
    if n is None:
        n = q.size
    if q.size != n:
        warnings.warn('incorrect register size?')
    display(Math('\mathrm{running\ circuit\ on\ set\ of\ basis\ states:}'))
    for ii in range(2 ** n):
        qc0 = QuantumCircuit(q)
        qc0.barrier(q[0])  # dummy circuit

        mm = []
        ij = ii
        for kk in range(n):
            mm += [ij % 2]
            if ij % 2 == 1:
                qc0.x(q[kk])
            ij = ij // 2
        inputstate = '|' + (' '.join(['%d' % m for m in mm[::-1]])) + '>'
        if 0:
            job = qiskit.execute(qc0, backend=backend)
            state_vector = job.result().get_statevector(qc0)
            inputstate = format_vector(state_vector)

        qc0 = qc0.combine(qc)

        job = qiskit.execute(qc0, backend=backend)
        state_vector = job.result().get_statevector(qc0)
        if verbose >= 2:
            print(state_vector)
        display(Math(inputstate + '\mathrm{transforms\ to}: ' + format_vector(state_vector)))


def n_controlled_Z(circuit, controls, target):
    """Implement a Z gate with multiple controls"""
    control_count = len(controls)
    if control_count == 1:
        circuit.h(target)
        circuit.cx(controls[0], target)
        circuit.h(target)
    elif control_count == 2:
        circuit.h(target)
        circuit.ccx(controls[0], controls[1], target)
        circuit.h(target)
    else:
        raise ValueError('CZ with {} controls is not implemented'.format(control_count))


def inversion_about_average(circuit, f_in, n):
    """Apply inversion about the average step of Grover's algorithm."""
    # Hadamards everywhere
    if n == 1:
        circuit.x(f_in[0])
        return
    for j in range(n):
        circuit.h(f_in[j])
    # D matrix: flips the sign of the state |000> only
    for j in range(n):
        circuit.x(f_in[j])
    n_controlled_Z(circuit, [f_in[j] for j in range(n - 1)], f_in[n - 1])
    for j in range(n):
        circuit.x(f_in[j])
    # Hadamards everywhere again
    for j in range(n):
        circuit.h(f_in[j])
