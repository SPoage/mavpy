#!/usr/bin/env python
from setuptools import setup, find_packages


setup(name='mavpy',
      version='0.1.0',
      description='MavPy Maven Integration Library',
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Environment :: Console',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: IBM Public License',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Java',
                   'Topic :: Software Development :: Build Tools',
                   'Topic :: Software Development :: Libraries'],
      url='https://github.com/SPoage/mavpy',
      author='Shane Poage',
      packages=find_packages(),
      install_requires=['kershaw'])