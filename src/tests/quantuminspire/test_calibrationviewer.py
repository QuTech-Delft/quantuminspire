""" Quantum Inspire SDK

Copyright 2018 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import sys
import contextlib
import io
from unittest import TestCase
from unittest.mock import Mock

from quantuminspire.calibration_viewer import CalibrationViewer


class TestCalibrationViewer(TestCase):

    def setUp(self):
        self.calibration = {'url': 'https://api.quantum-inspire.com/calibration/109006/',
                             'backend': 'https://api.quantum-inspire.com/backends/8/',
                             'parameters':
                                    {'system': {'fridge_temperature':
                                                    {'value': '20.9',
                                                     'unit': 'mK',
                                                     'symbol': 'Fridge temperature'},
                                               'last_calibration_date':
                                                   {'value': '04/11/2021 - 16:42 PM',
                                                    'unit': 'iso-8601',
                                                    'symbol': 'Calibration date'},
                                                'extra_field':
                                                    {'number': 0},
                                                'unknown_field': [0,1,2]
                                                },
                                    'qubits': {'q0':
                                                   {'t1':
                                                        {'value': 1.7341880614618646e-05,
                                                        'unit': 's',
                                                        'symbol': 'T1',
                                                        'decimals': 1},
                                                    't2star':
                                                        {'value': 2.6163761239800992e-05,
                                                        'unit': 's',
                                                        'symbol': 'T2e',
                                                        'decimals': 1},
                                                    'single_qubit_gate_fidelity':
                                                        {'value': 99.9,
                                                        'unit': '%',
                                                        'symbol': 'F1q'},
                                                    'two_qubit_gate_fidelity':
                                                        {'value': 98.1,
                                                         'unit': '%',
                                                         'symbol': 'F2q'},
                                                    'initialization_fidelity':
                                                        {'value': 99.7,
                                                         'unit': '%',
                                                         'symbol': 'Finit'},
                                                    'readout_fidelity':
                                                        {'value': 94.8,
                                                         'unit': '%',
                                                         'symbol': 'FR/O'},
                                                    'extra_field':
                                                        {'number': 0},
                                                    'unknown_field': [0,1,2]
                                                    }
                                               }
                                    }
                            }

        self.viewer = CalibrationViewer(self.calibration)

    def test_calibration_property(self):
        self.assertIsInstance(self.viewer.calibration, dict)
        self.assertEquals(self.viewer.calibration, self.calibration)

    def test_timestamp_property(self):
        self.assertIsInstance(self.viewer.timestamp, str)
        self.assertEquals(self.viewer.timestamp,
              self.calibration['parameters']['system']['last_calibration_date']['value'])

    def test_show_system_parameters(self):
        with contextlib.redirect_stdout(io.StringIO()) as s:
            self.viewer.show_system_parameters()

        output = s.getvalue()
        self.assertIn('fridge_temperature', output)
        self.assertIn('20.9', output)
        self.assertIn('last_calibration_date', output)
        self.assertIn('04/11/2021 - 16:42 PM', output)
        self.assertIn('Unknown structure', output)

    def test_show_qubit_parameters(self):
        with contextlib.redirect_stdout(io.StringIO()) as s:
            self.viewer.show_qubit_parameters()

        output = s.getvalue()
        self.assertIn('two_qubit_gate_fidelity', output)
        self.assertIn('98.1', output)
        self.assertIn('t1', output)
        self.assertIn('t2star', output)
        self.assertIn('extra_field', output)
        self.assertIn('0', output)
        self.assertIn('Unknown structure', output)


    def test_get_calibration_field(self):
        self.assertEquals(self.viewer.get_calibration_field('fridge_temperature'),
            {'value': '20.9', 'unit': 'mK', 'symbol': 'Fridge temperature'})

        with self.assertRaises(KeyError):
            self.viewer.get_calibration_field('wrong_field')

    def test_show_calibration_field(self):
        with contextlib.redirect_stdout(io.StringIO()) as s:
            self.viewer.show_calibration_field('fridge_temperature')

        output = s.getvalue()
        self.assertIn('fridge_temperature', output)
        self.assertIn('20.9', output)

        with contextlib.redirect_stdout(io.StringIO()) as s:
            self.viewer.show_calibration_field('extra_field')

        output = s.getvalue()
        self.assertIn('extra_field', output)
        self.assertIn('0', output)

    def test_repr(self):
        self.assertEquals(self.viewer.__repr__(),
            "<calibration of backend https://api.quantum-inspire.com/backends/8/ from time 04/11/2021 - 16:42 PM>")

    def test_str(self):
        with contextlib.redirect_stdout(io.StringIO()) as s:
            print(self.viewer.__str__())

        output = s.getvalue()
        self.assertIn('parameters', output)
        self.assertIn('qubits', output)
        self.assertIn('single_qubit_gate_fidelity', output)

    def test_import_error(self):
        class NoRprint():
            def find_module(self, f, p):
                if f.startswith('rprint'):
                    raise ImportError

        sys.path.insert(0, NoRprint())
        # now rprint ImportError should be triggered
        self.viewer = CalibrationViewer(self.calibration)
