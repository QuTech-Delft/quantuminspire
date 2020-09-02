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


def get_long_description():
    """ Extract the long description from the README file """

    with open('README.md', encoding='utf-8') as f:
        long_description = f.read()

    return long_description


setup(name='quantuminspire',
      description='SDK for the Quantum Inspire platform',
      long_description=get_long_description(),
      long_description_content_type='text/markdown',
      version=get_version_number('quantuminspire'),
      author='QuantumInspire',
      python_requires='>=3.6',
      package_dir={'': 'src'},
      data_files=[('share/doc/quantuminspire/examples',
                    ['docs/example_qiskit_entangle.py',
                     'docs/example_projectq_entangle.py',
                     'docs/example_projectq_grover.py',
                     'docs/example_projectq.ipynb',
                     'docs/grover_algorithm_qi.ipynb',
                     'docs/qi-performance-test.ipynb',
                     'docs/grover-qi.png',
                     'docs/classifier_example/data_plotter.py',
                     'docs/classifier_example/classification_example1_2_data_points.ipynb',
                     'docs/classifier_example/classification_example2_4_data_points.ipynb',
                     'docs/classifier_example/classification_example3_4_features.ipynb']),
                  ('share/doc/quantuminspire/examples/images',
                    ['docs/classifier_example/images/4pointsclassifier.png',
                     'docs/classifier_example/images/experimentaltest.png',
                     'docs/classifier_example/images/full_circuit.png',
                     'docs/classifier_example/images/fullalgorithm.png',
                     'docs/classifier_example/images/partb.png',
                     'docs/classifier_example/images/partc.png',
                     'docs/classifier_example/images/partf.png',
                     'docs/classifier_example/images/plot.png',
                     'docs/classifier_example/images/randompoint.png',
                     'docs/classifier_example/images/stateprep.png']),
                  ('share/doc/quantuminspire/examples/images/images4features',
                   ['docs/classifier_example/images/images4features/rotations.png']),
                  ('share/doc/quantuminspire/examples/images/images4points',
                   ['docs/classifier_example/images/images4points/datapoints.png',
                    'docs/classifier_example/images/images4points/parta.png',
                    'docs/classifier_example/images/images4points/partb.png',
                    'docs/classifier_example/images/images4points/partc.png',
                    'docs/classifier_example/images/images4points/partd.png',
                    'docs/classifier_example/images/images4points/parte.png'])
                 ],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'License :: OSI Approved :: Apache Software License'],
      license='Apache 2.0',
      packages=['quantuminspire', 'quantuminspire.qiskit', 'quantuminspire.projectq'],
      install_requires=['pytest>=3.3.1', 'coverage>=4.5.1', 'matplotlib>=2.1', 'pylatexenc',
                        'coreapi>=2.3.3', 'numpy>=1.17', 'jupyter', 'nbimporter', 'sklearn'],
      extras_require={'qiskit': ["qiskit>=0.20.0"], 'projectq': ["projectq>=0.4"]})
