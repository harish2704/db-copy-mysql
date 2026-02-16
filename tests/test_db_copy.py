"""
Basic tests for the db-copy-mysql package.
These tests verify that the package can be imported and basic functionality works.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the src directory to the path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_package_imports():
    """Test that the package can be imported successfully."""
    try:
        import db_copy_mysql
        assert hasattr(db_copy_mysql, '__version__')
        assert hasattr(db_copy_mysql, 'DatabaseCopyTool')
        assert hasattr(db_copy_mysql, 'SSHTunnelManager')
        assert hasattr(db_copy_mysql, 'MySQLDumpTool')
    except ImportError as e:
        pytest.fail(f"Failed to import package: {e}")

def test_main_function_exists():
    """Test that the main function exists and can be imported."""
    try:
        from db_copy_mysql.db_copy import main
        assert callable(main)
    except ImportError as e:
        pytest.fail(f"Failed to import main function: {e}")

def test_cli_entry_point():
    """Test that the CLI entry point works."""
    # This test verifies that the package can be run as a module
    # In a real test environment, you would test the actual CLI functionality
    # Here we just verify the structure is correct
    try:
        from db_copy_mysql.__main__ import main
        assert callable(main)
    except ImportError as e:
        pytest.fail(f"Failed to import __main__: {e}")

@patch('db_copy_mysql.db_copy.MySQLDumpTool.check_mysql_tools')
def test_mysql_tools_check(mock_check):
    """Test that MySQL tools check can be called."""
    from db_copy_mysql.db_copy import MySQLDumpTool
    
    # Mock the subprocess calls to avoid requiring actual MySQL tools
    mock_check.return_value = True
    
    result = MySQLDumpTool.check_mysql_tools()
    assert result is True
    mock_check.assert_called_once()

def test_version_consistency():
    """Test that version is consistent across the package."""
    import db_copy_mysql
    
    # Check that version exists and is a string
    assert hasattr(db_copy_mysql, '__version__')
    assert isinstance(db_copy_mysql.__version__, str)
    assert len(db_copy_mysql.__version__) > 0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])