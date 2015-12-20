#!/usr/bin/env python3
 
from setuptools import setup, find_packages
import msf

setup(
    name='msf',
    description = 'Framework to develop API REST',
    version=msf.__version__,
    plateformes='ALL',
    author='Vincent MAILLOL',
    author_email='vincent.maillol@gmail.com',
    keywords='framework REST WSGI DATABASE ORM',
    licence=msf.__license__,
    packages=['msf', 'msf.server'],
    entry_points={
        'console_scripts': [
            'msf = msf.__main__:main',
        ]
    }
)
