from setuptools import setup, find_packages
from distutils.version import StrictVersion
from importlib import import_module
import platform
import re

def readme():
    with open('README.md', encoding='utf-8') as f:
        return f.read()

def get_version(module, verbose=1):
    """ Extract version information from source code """

    try:
        with open('%s/version.py' % module, 'r') as f:
            ln = f.readline()
            m = re.search('.* ''(.*)''', ln)
            version = (m.group(1)).strip('\'')
    except Exception as E:
        print(E)
        version = 'none'
    if verbose:
        print('get_version: %s' % version)
    return version


print('packages: %s' % find_packages())


setup(name='quantuminspire',
      version=get_version('quantuminspire'),
      use_2to3=False,
      author='Pieter Eendebak',
      author_email='pieter.eendebak@tno.nl',
      maintainer='Pieter Eendebak',
      maintainer_email='pieter.eendebak@tno.nl',
      description='SDK for the Quantum Inspire platform',
      long_description=readme(),
      url='http://qutech.nl',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Science/Research',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Scientific/Engineering'
      ],
      license='Private',
      # if we want to install without tests:
      # packages=find_packages(exclude=["*.tests", "tests"]),
      packages=find_packages(),
      extras_require={
          'qiskit':  ["qiskit>=0.5.7", 'colorama', 'jupyter'],
      },
      install_requires=[
          'numpy', 'requests'
      ],
      )

