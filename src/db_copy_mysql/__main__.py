#!/usr/bin/env python3
"""
Entry point for the db-copy-mysql CLI command.
This allows the package to be run as: python -m db_copy_mysql
"""

from .db_copy import main

if __name__ == '__main__':
    main()