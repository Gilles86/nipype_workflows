#!/usr/bin/env python

#from distutils.core import setup
from setuptools import setup

def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration

    config = Configuration(None, parent_package, top_path)
    config.add_subpackage('gilles_workflows')
    return config

def main():
    from numpy.distutils.core import setup
    setup(name='gilles_workflows',
          version='0.1.1',
          description='NiPype workflows by Gilles',
          author='Gilles de Hollander',
          author_email='g.dehollander@uva.nl',
          url='http://www.gillesdehollander.nl',
          packages=['gilles_workflows'],
          configuration=configuration
         )

if __name__ == '__main__':
    main()
