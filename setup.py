""" Quantum Inspire SDK

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   https://www.apache.org/licenses/LICENSE-2.0

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


def get_long_description():
    """ Extract the long description from the README file """

    with open('README.md', encoding='utf-8') as f:
        long_description = f.read()

    return long_description


setup(name='quantuminspire',
      description='SDK for the Quantum Inspire platform',
      long_description=get_long_description(),
      long_description_content_type='text/markdown',
      url='https://qutech.nl',
      version=get_version_number('quantuminspire'),
      author='QuantumInspire',
      author_email='support@quantum-inspire.com',
      python_requires='>=3.8',
      package_dir={'': 'src'},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
          'License :: OSI Approved :: Apache Software License'],
      license='Apache 2.0',
      packages=['quantuminspire', 'quantuminspire.qiskit', 'quantuminspire.projectq'],
      install_requires=['coverage>=4.5.1', 'matplotlib>=2.1', 'pylatexenc', 'coreapi>=2.3.3', 'numpy>=1.20', 'jupyter',
                        'nbimporter', 'qilib', 'setuptools'],
      extras_require={
          "qiskit": ["qiskit>=1.0", "qiskit-aer"],
          "projectq": ["projectq>=0.8.0"],
          "dev": ["pytest>=3.3.1", "pylint", "mypy>=0.670"],
          "rtd": ["sphinx", "sphinx_rtd_theme", "nbsphinx", "sphinx-automodapi", "recommonmark"],
      })
