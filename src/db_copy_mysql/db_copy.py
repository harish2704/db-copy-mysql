#!/usr/bin/env python3
"""
MySQL Database Copy Tool
Copy data between MySQL databases using SSH tunneling and mysqldump
No external dependencies - uses system commands (ssh, mysqldump, mysql)
"""

import argparse
import sys
import json
import logging
import subprocess
import time
import tempfile
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """Manage SSH tunnel lifecycle"""
    
    def __init__(self, ssh_host: str, db_host: str, db_port: int, 
                 ssh_port: int = 22, ssh_user: Optional[str] = None, 
                 ssh_password: Optional[str] = None,
                 ssh_key: Optional[str] = None):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port or 22  # Default to standard SSH port
        self.ssh_user = ssh_user  # Can be empty to use SSH config
        self.db_host = db_host
        self.db_port = db_port
        self.ssh_password = ssh_password
        self.ssh_key = ssh_key and Path(ssh_key).expanduser()  # Expand ~ in path
        self.local_port = None
        self.process = None
    
    def find_free_port(self) -> int:
        """Find a free local port"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        _, port = sock.getsockname()
        sock.close()
        return port
    
    def start(self) -> int:
        """Start SSH tunnel and return local port"""
        self.local_port = self.find_free_port()
        
        # Format user@host or just host if user is not specified (uses SSH config)
        remote_spec = f"{self.ssh_user}@{self.ssh_host}" if self.ssh_user else self.ssh_host
        logger.info(f"Starting SSH tunnel: {remote_spec}:{self.ssh_port}")
        logger.info(f"Forwarding localhost:{self.local_port} -> {self.db_host}:{self.db_port}")
        
        ssh_cmd = [
            'ssh',
            '-N',  # Don't execute command
            '-L', f'{self.local_port}:{self.db_host}:{self.db_port}',
        ]
        
        # Add port (include even if 22 for clarity)
        ssh_cmd.extend(['-p', str(self.ssh_port)])
        
        # Add private key if specified
        if self.ssh_key:
            if not self.ssh_key.exists():
                logger.warning(f"SSH key not found: {self.ssh_key}")
            else:
                ssh_cmd.extend(['-i', str(self.ssh_key)])
        
        # Add compression for better performance over slow networks
        ssh_cmd.append('-C')
        
        ssh_cmd.append(remote_spec)
        
        try:
            # Start tunnel process
            self.process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )
            
            # Give tunnel time to establish
            time.sleep(1)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"SSH tunnel failed: {stderr.decode('utf-8', errors='ignore')}")
            
            logger.info(f"SSH tunnel established on localhost:{self.local_port}")
            return self.local_port
        
        except FileNotFoundError:
            logger.error("SSH command not found. Please install OpenSSH client.")
            raise
        except Exception as err:
            logger.error(f"Failed to start SSH tunnel: {err}")
            raise
    
    def stop(self):
        """Stop SSH tunnel"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("SSH tunnel closed")
            except subprocess.TimeoutExpired:
                self.process.kill()
                logger.warning("SSH tunnel forcefully terminated")
            except Exception as err:
                logger.error(f"Error closing SSH tunnel: {err}")


class MySQLDumpTool:
    """Handle MySQL dump and restore operations"""
    
    @staticmethod
    def parse_dump_columns(dump_file: str) -> Dict[str, List[str]]:
        """Parse SQL dump file to extract table names and their columns
        
        Returns a dict mapping table_name -> list of column names
        Looks for INSERT INTO statements with complete column lists
        """
        table_columns = {}
        
        try:
            with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    # Look for INSERT INTO statements with explicit column names
                    # Pattern: INSERT INTO `table_name` (col1, col2, ...) VALUES
                    if line.startswith('INSERT INTO'):
                        try:
                            # Extract table name - between backticks or unquoted
                            import re
                            
                            # Match: INSERT INTO `table` (cols) or INSERT INTO table (cols)
                            match = re.match(
                                r"INSERT\s+INTO\s+`?([^\s`(]+)`?\s*\(([^)]+)\)",
                                line,
                                re.IGNORECASE
                            )
                            
                            if match:
                                table_name = match.group(1)
                                columns_str = match.group(2)
                                
                                # Parse column names - remove backticks and split by comma
                                columns = [
                                    col.strip().strip('`')
                                    for col in columns_str.split(',')
                                ]
                                
                                table_columns[table_name] = columns
                        
                        except Exception as e:
                            logger.debug(f"Could not parse INSERT statement: {line[:100]} - {e}")
            
            if table_columns:
                logger.info(f"Parsed {len(table_columns)} tables from dump file")
                for table, cols in table_columns.items():
                    logger.debug(f"  {table}: {len(cols)} columns")
            else:
                logger.warning("No tables found in dump file")
        
        except Exception as err:
            logger.error(f"Error parsing dump file: {err}")
        
        return table_columns
    
    @staticmethod
    def get_target_columns(host: str, port: int, user: str, password: str,
                          database: str, table: str) -> List[str]:
        """Get list of column names from target database table
        
        Returns list of column names in the table
        """
        mysql_cmd = [
            'mysql',
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'--password={password}' if password else '--no-password',
            '-N',  # Skip column headers
            '-s',  # Silent mode (tab-separated)
            database
        ]
        
        try:
            process = subprocess.Popen(
                mysql_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION;"
            stdout, stderr = process.communicate(input=query.encode())
            
            if process.returncode != 0:
                logger.warning(f"Could not fetch columns for table '{table}': {stderr.decode()}")
                return []
            
            columns = [line.strip() for line in stdout.decode().split('\n') if line.strip()]
            return columns
        
        except Exception as err:
            logger.error(f"Error getting target columns: {err}")
            return []
    
    @staticmethod
    def add_missing_columns(host: str, port: int, user: str, password: str,
                           database: str, table: str, columns_to_add: List[str]) -> bool:
        """Add missing columns to target table as TEXT NULL
        
        Returns True if successful or no columns to add
        """
        if not columns_to_add:
            return True
        
        mysql_cmd = [
            'mysql',
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'--password={password}' if password else '--no-password',
            database
        ]
        
        try:
            alter_statements = []
            for col in columns_to_add:
                alter_statements.append(f"ADD COLUMN `{col}` TEXT NULL")
            
            alter_query = f"ALTER TABLE `{table}` {', '.join(alter_statements)};"
            
            logger.info(f"Adding {len(columns_to_add)} missing columns to table '{table}'")
            logger.debug(f"Columns to add: {columns_to_add}")
            
            process = subprocess.Popen(
                mysql_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(input=alter_query.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.warning(f"Could not add columns to table '{table}': {error_msg}")
                return False
            
            logger.info(f"Successfully added {len(columns_to_add)} columns to '{table}'")
            return True
        
        except Exception as err:
            logger.error(f"Error adding columns: {err}")
            return False
    
    @staticmethod
    def drop_columns(host: str, port: int, user: str, password: str,
                    database: str, table: str, columns_to_drop: List[str]) -> bool:
        """Remove columns from target table
        
        Returns True if successful or no columns to drop
        """
        if not columns_to_drop:
            return True
        
        mysql_cmd = [
            'mysql',
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'--password={password}' if password else '--no-password',
            database
        ]
        
        try:
            drop_statements = []
            for col in columns_to_drop:
                drop_statements.append(f"DROP COLUMN `{col}`")
            
            alter_query = f"ALTER TABLE `{table}` {', '.join(drop_statements)};"
            
            logger.info(f"Removing {len(columns_to_drop)} temporary columns from table '{table}'")
            logger.debug(f"Columns to remove: {columns_to_drop}")
            
            process = subprocess.Popen(
                mysql_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(input=alter_query.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.warning(f"Could not drop columns from table '{table}': {error_msg}")
                return False
            
            logger.info(f"Successfully removed {len(columns_to_drop)} columns from '{table}'")
            return True
        
        except Exception as err:
            logger.error(f"Error dropping columns: {err}")
            return False
    
    @staticmethod
    def check_mysql_tools() -> bool:
        """Check if mysqldump and mysql commands are available"""
        tools = ['mysqldump', 'mysql']
        missing = []
        
        for tool in tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                missing.append(tool)
        
        if missing:
            logger.error(f"Missing required tools: {', '.join(missing)}")
            logger.error("Please install MySQL client tools: apt-get install mysql-client")
            return False
        
        return True
    
    @staticmethod
    def dump_database(host: str, port: int, user: str, password: str, 
                      database: str, output_file: str, tables: Optional[List[str]] = None,
                      data_only: bool = False) -> bool:
        """Dump database to SQL file
        
        Args:
            host: Database host
            port: Database port
            user: Database user
            password: Database password
            database: Database name
            output_file: Output SQL file path
            tables: Specific tables to dump (optional)
            data_only: If True, dump only data (no schema). Includes column names for schema flexibility.
        """
        if data_only:
            logger.info(f"Dumping data-only (no schema) from database '{database}' at {host}:{port}")
        else:
            logger.info(f"Dumping database '{database}' (including schema) from {host}:{port}")
        
        mysqldump_cmd = [
            'mysqldump',
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'--password={password}' if password else '--no-password',
            '--single-transaction',
            '--lock-tables=false',
            database
        ]
        
        if data_only:
            mysqldump_cmd.extend([
                '--no-create-info',
                '--complete-insert',
                '--disable-keys'
            ])
            logger.info("Data-only mode: Including column names in INSERT statements for schema flexibility")
        else:
            mysqldump_cmd.extend([
                '--routines',
                '--triggers',
                '--events',
                '--create-options'
            ])
        
        # Add specific tables if provided
        if tables:
            mysqldump_cmd.extend(tables)
            logger.info(f"Dumping specific tables: {', '.join(tables)}")
        
        try:
            with open(output_file, 'w') as f:
                logger.info(f"Executing mysqldump command: {' '.join(mysqldump_cmd)}")
                process = subprocess.Popen(
                    mysqldump_cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    logger.error(f"mysqldump error: {error_msg}")
                    return False
            
            # Check file size
            file_size = os.path.getsize(output_file)
            logger.info(f"Database dump completed. File size: {file_size:,} bytes")
            
            if file_size == 0:
                logger.warning("Dump file is empty!")
                return False
            
            return True
        
        except FileNotFoundError:
            logger.error("mysqldump command not found. Install with: apt-get install mysql-client")
            return False
        except Exception as err:
            logger.error(f"Error during dump: {err}")
            return False
    
    @staticmethod
    def restore_database(host: str, port: int, user: str, password: str,
                        database: str, input_file: str, create_db: bool = True) -> bool:
        """Restore database from SQL file with error handling and line tracking"""
        logger.info(f"Restoring database '{database}' to {host}:{port}")
        
        # Create database first if needed
        if create_db:
            logger.info(f"Creating database '{database}' if not exists")
            create_cmd = [
                'mysql',
                '-h', host,
                '-P', str(port),
                '-u', user,
                f'--password={password}' if password else '--no-password',
            ]
            
            try:
                process = subprocess.Popen(
                    create_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                logger.info(f"Executing create database command: {' '.join(create_cmd)}")
                stdout, stderr = process.communicate(input=f"CREATE DATABASE IF NOT EXISTS `{database}`;\n".encode())
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    logger.warning(f"Create database message: {error_msg}")
            
            except Exception as err:
                logger.warning(f"Could not create database: {err}")
        
        # Restore from file with --force to ignore non-critical errors
        mysql_cmd = [
            'mysql',
            '--force',  # Continue on errors like SUPER privilege required
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'--password={password}' if password else '--no-password',
            database
        ]
        
        try:
            logger.info(f"Starting restore from file: {input_file}")
            logger.info("Using --force flag to continue on recoverable errors")
            
            with open(input_file, 'r') as f:
                process = subprocess.Popen(
                    mysql_cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = process.communicate()
                stderr_text = stderr.decode('utf-8', errors='ignore')
                stdout_text = stdout.decode('utf-8', errors='ignore')
                
                # Parse error messages and show corresponding lines from dump file
                if stderr_text:
                    MySQLDumpTool._handle_restore_errors(stderr_text, input_file)
                
                # With --force, mysql returns 0 even if there are errors in the output
                # Check if we have actual critical errors
                if "ERROR" in stderr_text.upper():
                    logger.warning(f"Restore completed with some errors (see above)")
                else:
                    logger.info(f"Database restore completed successfully")
            
            return True
        
        except FileNotFoundError:
            logger.error("mysql command not found. Install with: apt-get install mysql-client")
            return False
        except Exception as err:
            logger.error(f"Error during restore: {err}")
            return False
    
    @staticmethod
    def _handle_restore_errors(stderr_text: str, dump_file: str):
        """Parse SQL errors and show corresponding dump file lines"""
        lines = stderr_text.strip().split('\n')
        
        # Load dump file lines for reference
        try:
            with open(dump_file, 'r') as f:
                dump_lines = f.readlines()
        except Exception as err:
            logger.warning(f"Could not read dump file for error context: {err}")
            dump_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            
            # Parse error messages like: "ERROR 1227 (42000) at line 2281: Access denied..."
            if "ERROR" in line and "at line" in line:
                try:
                    # Extract line number from error message
                    parts = line.split("at line ")
                    if len(parts) > 1:
                        line_num_str = parts[1].split(":")[0]
                        line_num = int(line_num_str)
                        
                        # Extract error code and message
                        error_code = ""
                        error_msg = ""
                        if "ERROR" in line:
                            error_part = line.split("ERROR")[1]
                            error_msg = error_part.strip()
                        
                        logger.warning(f"{'='*70}")
                        logger.warning(f"Error at line {line_num}: {error_msg}")
                        logger.warning(f"{'='*70}")
                        
                        # Show the problematic line from dump file (with context)
                        if dump_lines and line_num > 0 and line_num <= len(dump_lines):
                            start_idx = max(0, line_num - 3)
                            end_idx = min(len(dump_lines), line_num + 2)
                            
                            logger.warning("Context from dump file:")
                            for i in range(start_idx, end_idx):
                                if i == line_num - 1:  # Line numbers are 1-indexed
                                    logger.warning(f">>> {i+1}: {dump_lines[i].rstrip()}")
                                else:
                                    logger.warning(f"    {i+1}: {dump_lines[i].rstrip()}")
                        else:
                            logger.warning(f"Could not display line {line_num} from dump file")
                
                except (ValueError, IndexError) as e:
                    # If we can't parse the line number, just log the error
                    logger.warning(line)
            else:
                # Log other warnings/errors
                if "WARNING" in line or "ERROR" in line:
                    logger.warning(line)


class DatabaseCopyTool:
    """Main database copy tool using SSH tunnels and mysqldump"""
    
    def __init__(self, source_config: Dict[str, Any], target_config: Dict[str, Any],
                 use_source_ssh: bool = False, use_target_ssh: bool = False,
                 data_only: bool = False, data_only_safe: bool = False):
        self.source_config = source_config
        self.target_config = target_config
        self.use_source_ssh = use_source_ssh
        self.use_target_ssh = use_target_ssh
        self.data_only = data_only
        self.data_only_safe = data_only_safe  # Safe mode with schema reconciliation
        self.source_tunnel = None
        self.target_tunnel = None
        self.dump_file = None
        self.added_columns = {}  # Track columns added during safe mode: {table: [cols]}
    
    def _setup_tunnel(self, config: Dict[str, Any], use_ssh: bool) -> tuple:
        """Setup SSH tunnel if needed and return host/port"""
        if use_ssh:
            ssh_config = config.get('ssh', {})
            tunnel = SSHTunnelManager(
                ssh_host=ssh_config['host'],
                db_host=config['host'],
                db_port=config.get('port', 3306),
                ssh_port=ssh_config.get('port', 22),
                ssh_user=ssh_config.get('username'),  # Optional - uses SSH config if not set
                ssh_password=ssh_config.get('password'),
                ssh_key=ssh_config.get('private_key_path')
            )
            local_port = tunnel.start()
            return '127.0.0.1', local_port, tunnel
        else:
            return config['host'], config.get('port', 3306), None
    
    def _cleanup_tunnel(self, tunnel: Optional[SSHTunnelManager]):
        """Cleanup SSH tunnel"""
        if tunnel:
            tunnel.stop()
    
    def _generate_dump_filename(self) -> str:
        """Generate unique SQL dump filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        source_db = self.source_config.get('database', 'db')
        filename = f"/tmp/db_dump_{source_db}_{timestamp}.sql"
        return filename
    
    def _reconcile_schema(self, target_host: str, target_port: int, target_user: str,
                         target_password: str, target_database: str) -> bool:
        """Analyze dump file and add missing columns to target database
        
        Compares dump file columns with target table columns and adds
        any missing columns as TEXT NULL to allow INSERT statements to work.
        
        Returns True if reconciliation completed (even with warnings)
        """
        try:
            # Parse dump file to get table/column info
            dump_tables = MySQLDumpTool.parse_dump_columns(self.dump_file)
            
            if not dump_tables:
                logger.warning("Could not parse tables from dump file")
                return False
            
            logger.info(f"Found {len(dump_tables)} tables in dump file")
            
            # For each table in dump, check target columns
            for table_name, dump_columns in dump_tables.items():
                logger.info(f"\nAnalyzing table '{table_name}'...")
                
                # Get existing columns in target table
                target_columns = MySQLDumpTool.get_target_columns(
                    host=target_host,
                    port=target_port,
                    user=target_user,
                    password=target_password,
                    database=target_database,
                    table=table_name
                )
                
                if not target_columns:
                    logger.warning(f"  Table '{table_name}' not found in target database or is empty")
                    continue
                
                logger.info(f"  Dump has {len(dump_columns)} columns")
                logger.info(f"  Target has {len(target_columns)} columns")
                
                # Find columns in dump but not in target
                missing_in_target = [col for col in dump_columns if col not in target_columns]
                
                if missing_in_target:
                    logger.warning(f"  Missing columns in target: {missing_in_target}")
                    
                    # Add missing columns to target
                    if MySQLDumpTool.add_missing_columns(
                        host=target_host,
                        port=target_port,
                        user=target_user,
                        password=target_password,
                        database=target_database,
                        table=table_name,
                        columns_to_add=missing_in_target
                    ):
                        self.added_columns[table_name] = missing_in_target
                else:
                    logger.info(f"  All dump columns exist in target table")
                
                # Warn about extra columns in target
                extra_in_target = [col for col in target_columns if col not in dump_columns]
                if extra_in_target:
                    logger.info(f"  Extra columns in target (will get NULL): {extra_in_target}")
            
            return True
        
        except Exception as err:
            logger.error(f"Error during schema reconciliation: {err}", exc_info=True)
            return False
    
    def copy_database(self, tables: Optional[List[str]] = None, 
                     keep_dump: bool = False, cleanup_temp_cols: bool = True) -> bool:
        """Copy database from source to target
        
        Args:
            tables: Specific tables to copy (optional)
            keep_dump: Keep the SQL dump file after copy
            cleanup_temp_cols: In safe mode, remove temporary columns added for schema mismatch
        """
        
        try:
            # Check required tools
            if not MySQLDumpTool.check_mysql_tools():
                return False
            
            # Setup source connection
            logger.info("Setting up source database connection...")
            source_host, source_port, self.source_tunnel = self._setup_tunnel(
                self.source_config, self.use_source_ssh
            )
            
            # Setup target connection
            logger.info("Setting up target database connection...")
            target_host, target_port, self.target_tunnel = self._setup_tunnel(
                self.target_config, self.use_target_ssh
            )
            
            # Generate dump filename
            self.dump_file = self._generate_dump_filename()
            
            # Dump source database
            if self.data_only or self.data_only_safe:
                logger.info("\n" + "="*50)
                logger.info("DUMPING SOURCE DATABASE (DATA ONLY)")
                logger.info("="*50)
            else:
                logger.info("\n" + "="*50)
                logger.info("DUMPING SOURCE DATABASE (WITH SCHEMA)")
                logger.info("="*50)
            
            if not MySQLDumpTool.dump_database(
                host=source_host,
                port=source_port,
                user=self.source_config['user'],
                password=self.source_config.get('password', ''),
                database=self.source_config['database'],
                output_file=self.dump_file,
                tables=tables,
                data_only=(self.data_only or self.data_only_safe)
            ):
                return False
            
            # Safe mode: reconcile schema before restore
            if self.data_only_safe:
                logger.info("\n" + "="*50)
                logger.info("SAFE MODE: ANALYZING SCHEMA DIFFERENCES")
                logger.info("="*50)
                
                if not self._reconcile_schema(target_host, target_port,
                                             self.target_config['user'],
                                             self.target_config.get('password', ''),
                                             self.target_config['database']):
                    logger.warning("Schema reconciliation had issues, but continuing with restore...")
            
            # Restore to target database
            if self.data_only or self.data_only_safe:
                logger.info("\n" + "="*50)
                logger.info("RESTORING DATA TO TARGET DATABASE")
                logger.info("="*50)
                logger.info("NOTE: Target database schema must already exist")
                logger.info("NOTE: Mismatched columns will be handled by mysqld")
            else:
                logger.info("\n" + "="*50)
                logger.info("RESTORING TO TARGET DATABASE (WITH SCHEMA)")
                logger.info("="*50)
            
            if not MySQLDumpTool.restore_database(
                host=target_host,
                port=target_port,
                user=self.target_config['user'],
                password=self.target_config.get('password', ''),
                database=self.target_config['database'],
                input_file=self.dump_file,
                create_db=True
            ):
                return False
            
            # Safe mode: cleanup temporary columns if requested
            if self.data_only_safe and cleanup_temp_cols and self.added_columns:
                logger.info("\n" + "="*50)
                logger.info("CLEANING UP TEMPORARY COLUMNS")
                logger.info("="*50)
                
                for table, cols in self.added_columns.items():
                    MySQLDumpTool.drop_columns(
                        host=target_host,
                        port=target_port,
                        user=self.target_config['user'],
                        password=self.target_config.get('password', ''),
                        database=self.target_config['database'],
                        table=table,
                        columns_to_drop=cols
                    )
            
            # Summary
            logger.info("\n" + "="*50)
            logger.info("COPY COMPLETED SUCCESSFULLY")
            logger.info("="*50)
            logger.info(f"Dump file: {self.dump_file}")
            
            if not keep_dump:
                logger.info("Cleaning up dump file...")
                try:
                    os.remove(self.dump_file)
                    logger.info("Dump file removed")
                except Exception as err:
                    logger.warning(f"Could not remove dump file: {err}")
            else:
                logger.info(f"Keeping dump file at: {self.dump_file}")
            
            return True
        
        except Exception as err:
            logger.error(f"Unexpected error: {err}", exc_info=True)
            return False
        
        finally:
            # Cleanup tunnels
            logger.info("\nCleaning up SSH tunnels...")
            self._cleanup_tunnel(self.source_tunnel)
            self._cleanup_tunnel(self.target_tunnel)


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as err:
        logger.error(f"Invalid JSON in config file: {err}")
        sys.exit(1)


def create_sample_config():
    """Print sample configuration"""
    sample = {
        "source": {
            "host": "source-db.example.com",
            "port": 3306,
            "user": "username",
            "password": "password",
            "database": "source_db"
        },
        "target": {
            "host": "target-db.example.com",
            "port": 3306,
            "user": "username",
            "password": "password",
            "database": "target_db"
        },
        "source_ssh": {
            "host": "source-server.example.com",
            "port": 22,
            "username": "ssh_user",
            "password": "ssh_password"
        },
        "target_ssh": {
            "host": "target-server.example.com",
            "port": 22,
            "username": "ssh_user",
            "private_key_path": "/path/to/private/key"
        }
    }
    
    print(json.dumps(sample, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='MySQL Database Copy Tool - Copy databases using SSH tunnels and mysqldump (No external dependencies)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Copy using config file
  python3 db_copy.py --config config.json

  # Copy data only (target schema must exist)
  python3 db_copy.py --config config.json --data-only

  # Copy data only with SAFE MODE - automatic schema reconciliation
  python3 db_copy.py --config config.json --data-only-safe
  # This will: analyze column differences, add missing columns to target,
  # import data, then remove temporary columns

  # Safe mode but keep the temporary columns added for schema mismatch
  python3 db_copy.py --config config.json --data-only-safe --keep-temp-cols

  # Copy specific tables
  python3 db_copy.py --config config.json --tables users products orders

  # Copy data from specific tables with safe mode
  python3 db_copy.py --config config.json --data-only-safe --tables users products

  # Keep the SQL dump file for manual inspection
  python3 db_copy.py --config config.json --keep-dump

  # Show sample config
  python3 db_copy.py --sample-config

  # Direct connection (no SSH)
  python3 db_copy.py \\
    --source-host source-db.com --source-user root --source-password pass --source-database mydb \\
    --target-host target-db.com --target-user root --target-password pass --target-database mydb

  # Data-only copy with direct connection
  python3 db_copy.py --data-only \\
    --source-host source-db.com --source-user root --source-password pass --source-database mydb \\
    --target-host target-db.com --target-user root --target-password pass --target-database mydb

  # Safe mode with direct connection (handles schema differences)
  python3 db_copy.py --data-only-safe \\
    --source-host source-db.com --source-user root --source-password pass --source-database mydb \\
    --target-host target-db.com --target-user root --target-password pass --target-database mydb
        """
    )
    
    parser.add_argument('--config', type=str, help='Path to JSON config file')
    parser.add_argument('--source-host', type=str, help='Source database host')
    parser.add_argument('--source-port', type=int, default=3306, help='Source database port (default: 3306)')
    parser.add_argument('--source-user', type=str, help='Source database user')
    parser.add_argument('--source-password', type=str, default='', help='Source database password')
    parser.add_argument('--source-database', type=str, help='Source database name')
    parser.add_argument('--source-ssh-host', type=str, help='Source SSH server host')
    parser.add_argument('--source-ssh-port', type=int, default=22, help='Source SSH port (default: 22)')
    parser.add_argument('--source-ssh-user', type=str, default=None, help='Source SSH username (optional, uses SSH config if not specified)')
    parser.add_argument('--source-ssh-password', type=str, help='Source SSH password')
    parser.add_argument('--source-ssh-key', type=str, help='Source SSH private key path (default: ~/.ssh/id_rsa)')
    
    parser.add_argument('--target-host', type=str, help='Target database host')
    parser.add_argument('--target-port', type=int, default=3306, help='Target database port (default: 3306)')
    parser.add_argument('--target-user', type=str, help='Target database user')
    parser.add_argument('--target-password', type=str, default='', help='Target database password')
    parser.add_argument('--target-database', type=str, help='Target database name')
    parser.add_argument('--target-ssh-host', type=str, help='Target SSH server host')
    parser.add_argument('--target-ssh-port', type=int, default=22, help='Target SSH port (default: 22)')
    parser.add_argument('--target-ssh-user', type=str, default=None, help='Target SSH username (optional, uses SSH config if not specified)')
    parser.add_argument('--target-ssh-password', type=str, help='Target SSH password')
    parser.add_argument('--target-ssh-key', type=str, help='Target SSH private key path (default: ~/.ssh/id_rsa)')
    
    parser.add_argument('--tables', nargs='+', help='Specific tables to copy (if not specified, all tables are copied)')
    parser.add_argument('--keep-dump', action='store_true', help='Keep the SQL dump file after copy')
    parser.add_argument('--data-only', action='store_true', help='Copy data only (no schema). Target database must have schema already. Handles schema differences gracefully.')
    parser.add_argument('--data-only-safe', action='store_true', help='Copy data only with automatic schema reconciliation. Adds missing columns to target, imports data, then removes temporary columns.')
    parser.add_argument('--keep-temp-cols', action='store_true', help='In safe mode, keep the temporary columns added for schema mismatch (do not delete them after import)')
    parser.add_argument('--sample-config', action='store_true', help='Print sample configuration')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Show sample config and exit
    if args.sample_config:
        create_sample_config()
        return 0
    
    # Load configuration
    if args.config:
        config = load_config_file(args.config)
        source_config = config.get('source', {})
        target_config = config.get('target', {})
        source_ssh_config = config.get('source_ssh', {})
        target_ssh_config = config.get('target_ssh', {})
    else:
        # Build config from command-line arguments
        if not all([args.source_host, args.source_user, args.source_database,
                   args.target_host, args.target_user, args.target_database]):
            parser.print_help()
            logger.error("Either --config file or all individual database arguments are required")
            return 1
        
        source_config = {
            'host': args.source_host,
            'port': args.source_port,
            'user': args.source_user,
            'password': args.source_password,
            'database': args.source_database
        }
        
        target_config = {
            'host': args.target_host,
            'port': args.target_port,
            'user': args.target_user,
            'password': args.target_password,
            'database': args.target_database
        }
        
        source_ssh_config = {
            'host': args.source_ssh_host,
            'port': args.source_ssh_port,
            'username': args.source_ssh_user,
            'password': args.source_ssh_password,
            'private_key_path': args.source_ssh_key
        } if args.source_ssh_host else {}
        
        target_ssh_config = {
            'host': args.target_ssh_host,
            'port': args.target_ssh_port,
            'username': args.target_ssh_user,
            'password': args.target_ssh_password,
            'private_key_path': args.target_ssh_key
        } if args.target_ssh_host else {}
        
        # Clean up None values to keep config clean
        if source_ssh_config:
            source_ssh_config = {k: v for k, v in source_ssh_config.items() if v is not None}
        if target_ssh_config:
            target_ssh_config = {k: v for k, v in target_ssh_config.items() if v is not None}
    
    # Add SSH config to main config if provided
    if source_ssh_config.get('host'):
        source_config['ssh'] = source_ssh_config
    
    if target_ssh_config.get('host'):
        target_config['ssh'] = target_ssh_config
    
    # Create tool and execute copy
    try:
        tool = DatabaseCopyTool(
            source_config=source_config,
            target_config=target_config,
            use_source_ssh=bool(source_config.get('ssh')),
            use_target_ssh=bool(target_config.get('ssh')),
            data_only=args.data_only,
            data_only_safe=args.data_only_safe
        )
        logger.info("Starting database copy operation...")
        logger.info("current configuration:")
        logger.info(f"Source Config: {source_config}")
        logger.info(f"Target Config: {target_config}")
        
        success = tool.copy_database(
            tables=args.tables,
            keep_dump=args.keep_dump,
            cleanup_temp_cols=not args.keep_temp_cols
        )
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as err:
        logger.error(f"Unexpected error: {err}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
