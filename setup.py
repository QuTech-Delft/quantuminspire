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

from setuptools import setup


def get_version_number(module):
    """ Extract the version number from the source code.

        Returns:
            Str: the version number.
    """
    with open('src/{}/version.py'.format(module), 'r') as file_stream:
        line = file_stream.readline().split()
        version_number = line[2].replace('\'', '')
    return version_number


setup(name='quantuminspire',
      description='SDK for the Quantum Inspire platform',
      version=get_version_number('quantuminspire'),
      author='QuantumInspire',
      python_requires='>=3.6',
      package_dir={'': 'src'},
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'License :: OSI Approved :: Apache Software License'],
      license='Apache 2.0',
      packages=['quantuminspire', 'quantuminspire.qiskit', 'quantuminspire.projectq'],
      install_requires=['pytest>=3.3.1', 'coverage>=4.5.1',
                        'coreapi>=2.3.3', 'numpy', 'jupyter'],
      extras_require={'qiskit': ["qiskit>=0.7.0, <0.8.0"], 'projectq': ["projectq>=0.4"]})
