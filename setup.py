#!/usr/bin/env python3
"""
Setup script for db-copy-mysql package.
This provides backward compatibility with older pip versions.
"""

import os
from setuptools import setup, find_packages

# Read README for long description
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="db-copy-mysql",
    version="1.0.0",
    author="Harish Karumuthil",
    author_email="harish2704@gmail.com",
    description="MySQL Database Copy Tool - Copy databases using SSH tunnels and mysqldump (No external dependencies)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/harish2704/db-copy-mysql",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: System :: Installation/Setup",
        "Topic :: Utilities"
    ],
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            'db-copy-mysql=db_copy_mysql.__main__:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)