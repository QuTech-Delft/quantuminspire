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
from typing import Any, Dict

import json
import numpy as np

try:
    from rich import print as rprint
except ImportError:
    rprint = print


class CalibrationViewer:

    def __init__(self, calibration_dictionary: Dict[str, Any]) -> None:
        """
        Object to view and nicely print backend calibration data returned by the API.

        :param calibration_dictionary: The calibration dictionary to be used by viewer.
        """
        self._calibration = calibration_dictionary
        return

    @property
    def calibration(self) -> Dict[str, Any]:
        return self._calibration

    @property
    def timestamp(self) -> str:
        return str(self.calibration['parameters']['system']['last_calibration_date']['value'])

    def show_system_parameters(self) -> None:
        """Print system calibration parameters."""
        system = self.calibration['parameters']['system']
        rprint(f'[green]System[/green]:')

        for key, item in system.items():
            if isinstance(item, dict):
                if np.all([k in item for k in ['unit', 'value']]):
                    rprint(f"\t{key}: {item['value']} [{item['unit']}]")
                else:
                    try:
                        rprint(f"\t{key}: calibration at {item['timestamp']}")
                    except KeyError:
                        rprint(f"Key 'timestamp' not in item {item}.")
            else:
                rprint(f"Unknown structure '{key}' in system calibration.")

    def show_qubit_parameters(self) -> None:
        """Print qubit calibration parameters."""
        qdata = self.calibration['parameters']['qubits']

        for qubit, data in qdata.items():
            rprint(f'[green]Qubit[/green]: {qubit}')
            for key, item in data.items():
                if isinstance(item, dict):
                    if np.all([k in item for k in ['unit', 'value']]):
                        rprint(f"\t{key}: {item['value']} [{item['unit']}]")
                    else:
                        rprint(f"\t{key}: {item}")
                else:
                    rprint(f"Unknown structure '{key}' in qubit calibration.")

    def get_calibration_field(self, field: str) -> Any:
        """
        Safely gets field `field` from system calibration.

        :raises KeyError: If key `field` does not exist in system calibration dictionary.

        :return: The system calibration content of `field`.
        """
        if field not in self.calibration['parameters']['system']:
            raise KeyError(f"Calibration field '{field}' does not exist in calibration dictionary.")

        return self.calibration['parameters']['system'][field]

    def show_calibration_field(self, field: str) -> Any:
        """
        Print calibration for a specific key `field` and return the content.
        Also prints standard subfields 'timestamp' and 'status', if they are available.

        :return: The system calibration content of `field`.
        """
        simple_keys = ['timestamp', 'status']
        cal = self.get_calibration_field(field)
        rprint(f'[green]Calibration[/green]: {field}')
        try:
            rprint(f"\t{cal['value']}")
        except KeyError:
            rprint(f"\t{cal}.")

        for key in simple_keys:
            try:
                rprint(f"\t[green]{key}[/green]: {cal[key]}")
            except KeyError:
                # print(f"Simple key '{key}' not in calibration dictionary.")
                pass

        other_fields = set(cal.keys()) - set(simple_keys)
        rprint(f"[green]other fields[/green]:", end='')
        rprint(f"\t{str(other_fields)}")

        return cal

    def __repr__(self) -> str:
        return f"<calibration of backend {self.calibration['backend']} from time {self.timestamp}>"

    def __str__(self) -> str:
        return json.dumps(self.calibration)

