#!/usr/bin/env python3
 
from setuptools import setup, find_packages
import woof

setup(
    name='woof',
    description = 'Framework to develop API REST',
    version=woof.__version__,
    plateformes='ALL',
    author='Vincent MAILLOL',
    author_email='vincent.maillol@gmail.com',
    keywords='framework REST WSGI DATABASE ORM',
    license=woof.__license__,
    packages=['woof', 'woof.server'],
    entry_points={
        'console_scripts': [
            'woof = woof.__main__:main',
        ]
    }
)
