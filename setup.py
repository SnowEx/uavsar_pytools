#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

test_requirements = ['pytest>=3', ]

setup(
    author="Zachary Marshall Keskinen",
    author_email='zachkeskinen@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="A set of tools to download and convert UAVSAR binary files",
    entry_points={
        'console_scripts': [
            'uavsar_pytools=uavsar_pytools.cli:main',
        ],
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='uavsar_pytools',
    name='uavsar_pytools',
    packages=find_packages(include=['uavsar_pytools', 'uavsar_pytools.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/ZachKeskinen/uavsar_pytools',
    version='0.1.0',
    zip_safe=False,
)
