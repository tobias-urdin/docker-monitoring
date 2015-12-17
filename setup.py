#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Docker Monitoring
# Copyright (C) 2015 Crystone Sverige AB

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os

from distutils.core import setup
from distutils.core import Command
from unittest import TextTestRunner, TestLoader
from subprocess import call


class TestCommand(Command):
    description = "run test"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        status = self._run_tests()
        sys.exit(status)

    def _run_tests(self):
        print "hello world"


class Pep8Command(Command):
    description = "run pep8"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        status = self._run_tests()
        sys.exit(status)

    def _run_tests(self):
        try:
            import pep8
            pep8
        except ImportError:
            print('Missing "pep8" library. You can install it using pip:'
                  'pip install pep8')
            sys.exit(1)

        cwd = os.getcwd()
        retcode = call(('pep8 %s/docker_monitoring/ %s/test/' %
                        (cwd, cwd)).split(' '))

        sys.exit(retcode)


class CoverageCommand(Command):
    description = "run coverage"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
           import coverage
        except ImportError:
            print('Missing "coverage" library. You can install it using pip:'
                  'pip install coverage')
            sys.exit(1)

        cover = coverage.coverage(config_file='.coveragerc')
        cover.start()

        tc = TestCommand(self.distribution)
        tc._run_tests()

        cover.stop()
        cover.save()
        cover.html_report()

setup(name='docker-monitoring',
      version='1.0',
      description='Docker Monitoring checks for Nagios.',
      author='Crystone Sverige AB',
      author_email='support@crystone.se',
      license='GNU GPL 2',
      packages=['docker_monitoring'],
      package_dir={
          'docker_monitoring': 'docker_monitoring',
      },
      url='https://github.com/crystone/docker-monitoring',
      cmdclass={
          'test': TestCommand,
          'pep8': Pep8Command,
          'coverage': CoverageCommand
      },
      )
