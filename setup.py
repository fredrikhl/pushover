#!/usr/bin/env python2
# encoding: utf-8
from setuptools import setup, find_packages

version = '1.1'

setup(name='pushover',
      author='Fredrik Larsen',
      author_email='fredrik.h.larsen@gmail.com',
      url='https://github.com/fredrikhl/pushover',
      description='Simple pushover cli program and library.',
      entry_points={
          'setuptools.installation': ['eggsecutable = pushover:main'],
          'console_scripts': ['pushover = pushover:main'], },
      version=version,
      license='GPL',
      packages=find_packages(), )
