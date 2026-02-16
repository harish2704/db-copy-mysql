"""
MySQL Database Copy Tool - Copy databases using SSH tunnels and mysqldump (No external dependencies)

This package provides a CLI tool to copy MySQL databases using SSH tunneling and system commands
(mysqldump, mysql). It has zero external Python dependencies and only uses the Python standard library.

Main features:
- SSH tunneling with key-based or password authentication
- Copy entire databases or specific tables
- Data-only copy mode with schema reconciliation
- Automatic database creation on target
- Config file or command-line support
- Detailed logging and error reporting

Usage:
    db-copy-mysql --config config.json
    db-copy-mysql --source-host source-db.com --target-host target-db.com
"""

__version__ = "1.0.0"
__author__ = "Harish Karumuthil"
__email__ = "harish2704@gmail.com"
__license__ = "MIT"

from .db_copy import DatabaseCopyTool, SSHTunnelManager, MySQLDumpTool

__all__ = [
    "DatabaseCopyTool",
    "SSHTunnelManager", 
    "MySQLDumpTool",
]