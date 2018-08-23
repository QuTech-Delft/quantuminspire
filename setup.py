from setuptools import setup


def get_version_number(module):
    """ Extract the version number from the source code.

        Returns:
            Str: the version number.
    """
    with open('src/{}/__init__.py'.format(module), 'r') as file_stream:
        line = file_stream.readline().split()
        version_number = line[2].replace('\'', '')
    return version_number


setup(name='quantuminspire',
      description='SDK for the Quantum Inspire platform',
      version=get_version_number('quantuminspire'),
      author='QuantumInspire',
      python_requires='>=3.5',
      package_dir={'': 'src'},
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7'],
      license='Other/Proprietary License',
      packages=['quantuminspire', 'quantuminspire.utils', 'quantuminspire.qiskit'],
      install_requires=['pytest>=3.3.1', 'coverage>=4.5.1',
                        'coreapi>=2.3.3', 'numpy', 'jupyter'],
      extras_require={'qiskit': ["qiskit>=0.5.7"], 'projectq': ["projectq>=0.4"]})
