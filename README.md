# MySQL Database Copy Tool (No External Dependencies)

A lightweight Python CLI tool to copy MySQL databases using SSH tunneling and system commands (mysqldump, mysql). **Zero external Python dependencies** - only uses standard library and system utilities.

## Features

- ✅ **No pip dependencies** - Uses only Python standard library
- ✅ **Faster** - Direct use of mysqldump (optimized tool)
- ✅ **More portable** - Relies on common system tools
- ✅ **Better for large databases** - mysqldump is more efficient
- ✅ **SSH tunneling** - Native OpenSSH support
- ✅ Copy entire databases or specific tables
- ✅ SSH tunneling with key-based or password authentication
- ✅ Different servers, ports, and database names
- ✅ Automatic database creation on target
- ✅ Batch processing optimized for large datasets
- ✅ Unique SQL dump files with timestamps
- ✅ Detailed logging and error reporting
- ✅ Config file or command-line support
- ✅ **Data-only copy mode** - Skip schema, copy only data
- ✅ **Safe mode with schema reconciliation** - Auto-handle column differences
- ✅ **Intelligent column matching** - Complete INSERT statements with explicit column names

## System Requirements

### Required

- Python 3.6+
- `ssh` command (OpenSSH client)
- `mysqldump` command (MySQL client)
- `mysql` command (MySQL client)

### Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install openssh-client mysql-client
chmod +x db_copy.py
```

**macOS (with Homebrew):**
```bash
brew install openssh mysql-client
chmod +x db_copy.py
```

**CentOS/RHEL:**
```bash
sudo yum install openssh-clients mysql
chmod +x db_copy.py
```

## Usage

### 1. Using Configuration File (Recommended)

Create `config.json`:
```json
{
  "source": {
    "host": "prod-db.example.com",
    "port": 3306,
    "user": "db_user",
    "password": "db_pass",
    "database": "production_db"
  },
  "target": {
    "host": "dev-db.example.com",
    "port": 3306,
    "user": "db_user",
    "password": "db_pass",
    "database": "dev_db"
  }
}
```

Run:
```bash
python3 db_copy.py --config config.json
```

### 2. Direct Connection (No SSH)

```bash
python3 db_copy.py \
  --source-host prod-db.example.com \
  --source-user root \
  --source-password secret123 \
  --source-database mydb \
  --target-host dev-db.example.com \
  --target-user root \
  --target-password secret456 \
  --target-database mydb
```

### 3. With SSH Tunneling (Password Auth)

Config file:
```json
{
  "source": {
    "host": "internal-db.local",
    "port": 3306,
    "user": "dbuser",
    "password": "dbpass",
    "database": "mydb"
  },
  "source_ssh": {
    "host": "bastion.example.com",
    "port": 22,
    "username": "ubuntu",
    "password": "ssh_password"
  },
  "target": {
    "host": "localhost",
    "port": 3306,
    "user": "dbuser",
    "password": "dbpass",
    "database": "mydb"
  }
}
```

Run:
```bash
python3 db_copy.py --config config.json
```

### 4. SSH with Key-Based Authentication

Config file:
```json
{
  "source": {
    "host": "db.internal.local",
    "port": 3306,
    "user": "dbuser",
    "password": "dbpass",
    "database": "mydb"
  },
  "source_ssh": {
    "host": "bastion.example.com",
    "port": 22,
    "username": "ubuntu",
    "private_key_path": "/home/user/.ssh/bastion_key"
  },
  "target": {
    "host": "localhost",
    "port": 3306,
    "user": "dbuser",
    "password": "dbpass",
    "database": "mydb"
  }
}
```

Run:
```bash
python3 db_copy.py --config config.json
```

### 5. Copy Specific Tables

```bash
python3 db_copy.py --config config.json --tables users products orders
```

### 6. Keep SQL Dump File

```bash
python3 db_copy.py --config config.json --keep-dump
```

The dump file location will be printed to stdout. Default location: `/tmp/db_dump_<database>_<timestamp>.sql`

### 7. Verbose Logging

```bash
python3 db_copy.py --config config.json --verbose
```

### 8. Show Sample Config

```bash
python3 db_copy.py --sample-config
```

## Data-Only Copy Mode

Copy only data without schema. Useful when target database already has the schema defined.

### Basic Data-Only Mode

```bash
python3 db_copy.py --config config.json --data-only
```

**Requirements:**
- Target database and tables must already exist
- Source and target schemas should match (or have compatible column names)

**How it works:**
- Uses `mysqldump --no-create-info` to skip CREATE TABLE statements
- Uses `mysqldump --complete-insert` to include column names in INSERT statements
- Allows partial schema matching - extra columns in target get NULL values

### Safe Mode - Schema Reconciliation

For scenarios where source and target have different schemas:

```bash
python3 db_copy.py --config config.json --data-only-safe
```

**Features:**
- ✅ Automatically detects column differences
- ✅ Adds missing columns to target as TEXT NULL
- ✅ Imports data using complete INSERT statements
- ✅ Removes temporary columns after successful import
- ✅ Handles extra columns gracefully (NULL values)

**What happens in safe mode:**

1. Dump data from source (with explicit column names)
2. Parse dump file to extract table and column information
3. Query target database for existing columns
4. Add any missing columns as `TEXT NULL`
5. Import data into target
6. Remove temporary columns (can be kept with `--keep-temp-cols`)

**Example with schema differences:**

Source table `users`:
```sql
id, name, email, phone, created_at, updated_at
```

Target table `users`:
```sql
id, name, email, department, status
```

Safe mode will:
- Add `phone`, `created_at`, `updated_at` to target as TEXT NULL
- Skip `department` and `status` columns (they'll be NULL in INSERT)
- Remove temporary columns after import

### Safe Mode Options

```bash
# Safe mode with schema reconciliation
python3 db_copy.py --config config.json --data-only-safe

# Safe mode but keep temporary columns
python3 db_copy.py --config config.json --data-only-safe --keep-temp-cols

# Safe mode for specific tables
python3 db_copy.py --config config.json --data-only-safe --tables users products
```

### Data-Only Copy Scenarios

```bash
# Basic data-only (schemas match)
python3 db_copy.py --config config.json --data-only

# Safe mode (schemas may differ)
python3 db_copy.py --config config.json --data-only-safe

# Specific tables only
python3 db_copy.py --config config.json --data-only --tables orders transactions

# Safe mode with specific tables
python3 db_copy.py --config config.json --data-only-safe --tables orders transactions

# With SSH tunneling (data-only)
python3 db_copy.py --config config.json --data-only --keep-dump
```

### 9. Verbose Logging

```bash
python3 db_copy.py --config config.json --verbose
```

### 10. Show Sample Config

```bash
python3 db_copy.py --sample-config
```

## How It Works

### Full Database Copy with Schema

1. **SSH Tunnel Setup** (if needed)
   - Creates SSH tunnel to source server using `ssh -L`
   - Creates SSH tunnel to target server using `ssh -L`
   - Auto-assigns available local ports

2. **Database Dump**
   - Uses `mysqldump` with optimized flags:
     - `--single-transaction`: Single consistent snapshot
     - `--lock-tables=false`: No lock wait
     - `--routines`: Include stored procedures
     - `--triggers`: Include triggers
     - `--events`: Include scheduled events

3. **SQL File Generation**
   - Creates unique timestamped file: `/tmp/db_dump_<db>_<timestamp>.sql`
   - Allows multiple concurrent operations

4. **Database Restore**
   - Creates target database if it doesn't exist
   - Pipes SQL file to `mysql` command
   - Clean restoration with no temporary files needed

5. **Cleanup**
   - Removes SQL dump file (unless `--keep-dump` is set)
   - Closes SSH tunnels

### Data-Only Copy

1. **Database Dump (Data Only)**
   - Uses `mysqldump --no-create-info` (skip schema)
   - Uses `mysqldump --complete-insert` (explicit column names)
   - Uses `mysqldump --disable-keys` (faster restore)

2. **Optional: Schema Reconciliation** (Safe Mode)
   - Parses dump file to extract table/column information
   - Queries `INFORMATION_SCHEMA` on target database
   - Identifies missing columns in target tables
   - Adds missing columns as `TEXT NULL` to target
   - Tracks added columns for cleanup

3. **Data Restore**
   - Complete INSERT statements work with mismatched schemas
   - Explicitly-named columns allow flexible column matching
   - Extra columns in target receive NULL values

4. **Post-Restore Cleanup** (Safe Mode)
   - Removes temporary columns added during reconciliation
   - Can be skipped with `--keep-temp-cols` flag

## Configuration File Reference

### Minimal Config (Direct Connection)

```json
{
  "source": {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "mydb"
  },
  "target": {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "mydb"
  }
}
```

### Full Config (With SSH)

```json
{
  "source": {
    "host": "db.internal",
    "port": 3306,
    "user": "dbuser",
    "password": "dbpass",
    "database": "production"
  },
  "source_ssh": {
    "host": "bastion.example.com",
    "port": 22,
    "username": "sshuser",
    "password": "sshpass",
    "private_key_path": "/path/to/key"
  },
  "target": {
    "host": "db.local",
    "port": 3306,
    "user": "dbuser",
    "password": "dbpass",
    "database": "development"
  },
  "target_ssh": {
    "host": "bastion2.example.com",
    "port": 22,
    "username": "sshuser",
    "password": "sshpass",
    "private_key_path": "/path/to/key"
  }
}
```

## CLI Reference

### Main Flags

| Flag | Type | Description |
|------|------|-------------|
| `--config` | path | Path to JSON config file |
| `--verbose` | flag | Enable verbose logging |
| `--sample-config` | flag | Print sample configuration and exit |

### Data Copy Flags

| Flag | Type | Description |
|------|------|-------------|
| `--tables` | list | Specific tables to copy (space-separated) |
| `--keep-dump` | flag | Keep SQL dump file after copy |

### Data-Only Mode Flags

| Flag | Type | Description |
|------|------|-------------|
| `--data-only` | flag | Copy data only (no schema). Requires target schema to exist. |
| `--data-only-safe` | flag | Copy data only with automatic schema reconciliation. Handles column differences. |
| `--keep-temp-cols` | flag | In safe mode, don't remove temporary columns after import |

### Source Database Flags

| Flag | Type | Description |
|------|------|-------------|
| `--source-host` | string | Source database host |
| `--source-port` | int | Source database port (default: 3306) |
| `--source-user` | string | Source database user |
| `--source-password` | string | Source database password |
| `--source-database` | string | Source database name |

### Source SSH Flags

| Flag | Type | Description |
|------|------|-------------|
| `--source-ssh-host` | string | Source SSH server host |
| `--source-ssh-port` | int | Source SSH server port (default: 22) |
| `--source-ssh-user` | string | Source SSH username (optional, uses SSH config if not specified) |
| `--source-ssh-password` | string | Source SSH password |
| `--source-ssh-key` | path | Source SSH private key path |

### Target Database Flags

| Flag | Type | Description |
|------|------|-------------|
| `--target-host` | string | Target database host |
| `--target-port` | int | Target database port (default: 3306) |
| `--target-user` | string | Target database user |
| `--target-password` | string | Target database password |
| `--target-database` | string | Target database name |

### Target SSH Flags

| Flag | Type | Description |
|------|------|-------------|
| `--target-ssh-host` | string | Target SSH server host |
| `--target-ssh-port` | int | Target SSH server port (default: 22) |
| `--target-ssh-user` | string | Target SSH username (optional, uses SSH config if not specified) |
| `--target-ssh-password` | string | Target SSH password |
| `--target-ssh-key` | path | Target SSH private key path |



### Scenario 1: Copy Local Database

```bash
python3 db_copy.py \
  --source-host localhost \
  --source-user root \
  --source-password pass \
  --source-database old_db \
  --target-host localhost \
  --target-user root \
  --target-password pass \
  --target-database new_db
```

### Scenario 2: Production to Dev (Different Servers)

```bash
python3 db_copy.py \
  --source-host prod-db.aws.com \
  --source-user admin \
  --source-password prod_pass \
  --source-database production \
  --target-host dev-db.local \
  --target-user admin \
  --target-password dev_pass \
  --target-database development
```

### Scenario 3: Through SSH Bastion

```bash
python3 db_copy.py \
  --source-host 10.0.1.5 \
  --source-user dbuser \
  --source-password dbpass \
  --source-database mydb \
  --source-ssh-host bastion.example.com \
  --source-ssh-user ubuntu \
  --source-ssh-key ~/.ssh/bastion_key \
  --target-host localhost \
  --target-user root \
  --target-password rootpass \
  --target-database mydb
```

### Scenario 4: Copy Specific Tables Only

```bash
python3 db_copy.py --config config.json --tables users clients projects
```

### Scenario 5: Keep Dump for Inspection

```bash
python3 db_copy.py --config config.json --keep-dump
# Output shows: Keeping dump file at: /tmp/db_dump_mydb_20260130_143022.sql
```

### Scenario 6: Data-Only Copy (Matching Schemas)

```bash
python3 db_copy.py \
  --source-host prod-db.aws.com \
  --source-user admin \
  --source-password prod_pass \
  --source-database production \
  --target-host dev-db.local \
  --target-user admin \
  --target-password dev_pass \
  --target-database development \
  --data-only
```

### Scenario 7: Safe Mode Copy (Schema Mismatch)

Source and target have different schemas - uses safe mode to auto-reconcile:

```bash
python3 db_copy.py \
  --source-host prod-db.aws.com \
  --source-user admin \
  --source-password prod_pass \
  --source-database production \
  --target-host dev-db.local \
  --target-user admin \
  --target-password dev_pass \
  --target-database development \
  --data-only-safe
```

Or with config:

```bash
python3 db_copy.py --config config.json --data-only-safe
```

### Scenario 8: Safe Mode with Specific Tables

```bash
python3 db_copy.py --config config.json --data-only-safe --tables users orders transactions
```

### Scenario 9: Safe Mode Keeping Temporary Columns

```bash
python3 db_copy.py --config config.json --data-only-safe --keep-temp-cols
```

Useful if you want to manually inspect or validate the added columns before removing them.

## Troubleshooting

### Error: "mysql command not found"

```
mysql: command not found
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install mysql-client

# macOS
brew install mysql-client

# CentOS/RHEL
sudo yum install mysql
```

### Error: "mysqldump command not found"

Same solution as above - install mysql-client.

### SSH Connection Timeout

```
ssh: connect to host bastion.example.com port 22: Connection timed out
```

**Solutions:**
- Check firewall rules allow SSH (port 22)
- Verify hostname/IP is correct
- Check network connectivity: `ping bastion.example.com`
- Try: `ssh -v ubuntu@bastion.example.com` for debugging

### Permission Denied (SSH Key)

```
Permission denied (publickey,password)
```

**Solutions:**
- Check key file permissions: `chmod 600 ~/.ssh/id_rsa`
- Verify key is correct: `ssh-keygen -l -f ~/.ssh/id_rsa`
- Try with password instead: Remove `private_key_path`, add `password`

### MySQL Connection Refused

```
ERROR 2003 (HY000): Can't connect to MySQL server on 'localhost:3306'
```

**Solutions:**
- Verify MySQL is running
- Check host and port are correct
- Verify credentials
- Try direct connection first: `mysql -h localhost -u root -p`

### "Access Denied" Error

```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

**Solutions:**
- Verify username is correct
- Verify password is correct
- Check user has appropriate privileges
- Test: `mysql -h host -u user -p -e "SELECT 1;"`

### Dump File is Empty

```
WARNING: Dump file is empty!
```

**Solutions:**
- Verify source database exists
- Verify user has SELECT permission
- Check if tables exist: `mysql -h host -u user -p -e "USE db; SHOW TABLES;"`

### SSH Tunnel Not Establishing

```
SSH tunnel failed: Permission denied (publickey,password)
```

**Solutions:**
- Verify SSH credentials
- Check SSH server is accessible
- Try manual connection: `ssh user@host`

## Data-Only Copy Best Practices

### When to Use Each Mode

| Mode | Use Case | Schema Requirement |
|------|----------|-------------------|
| **Full Copy** | Fresh target environment | Target can be empty or new |
| **Data-Only** | Target schema matches source | Identical or compatible schemas |
| **Data-Only Safe** | Schema has differences | Any schema (auto-reconciles) |

### Safe Mode Column Handling

**Scenario 1: Source has extra column**
```
Source: id, name, email, phone
Target: id, name, email
Result: phone column added to target as TEXT NULL
        Data imported successfully
        Temporary column removed (optional)
```

**Scenario 2: Target has extra column**
```
Source: id, name, email
Target: id, name, email, department, status
Result: All source columns imported
        department, status get NULL values
        No temporary columns added
```

**Scenario 3: Column name mismatch (Different schema)**
```
Source: user_id, user_name
Target: id, name
Result: Fails (column names must match)
        Solution: Rename columns in target before import
                  or use basic --data-only mode if can handle mismatch
```

## Performance Tips

1. **Large Databases**: For multi-gigabyte databases, consider:
   - Running on a machine close to both servers
   - Using a persistent SSH connection
   - Keeping `--keep-dump` to preserve a backup
   - Using `--data-only` for faster incremental updates

2. **Network Optimization**:
   - SSH via LAN is faster than over internet
   - Consider gzip compression if network-bound
   - Run during off-peak hours
   - Data-only mode is faster than full copy (no schema processing)

3. **Database Optimization**:
   - Specific table copy is faster than full database
   - Indexes are included automatically
   - Foreign key constraints are preserved
   - Safe mode adds overhead for schema analysis (minimal)

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use SSH key authentication** instead of passwords when possible
3. **Secure private keys**: `chmod 600 ~/.ssh/id_rsa`
4. **Use strong passwords** for database users
5. **Restrict network access** to database servers
6. **Use environment-specific credentials** (dev/prod/staging)
7. **Review SQL dump files** if `--keep-dump` is used
8. **Protect dump files** when using `--keep-dump` (may contain sensitive data)

## Data-Only Copy Security

When using data-only modes (`--data-only`, `--data-only-safe`):

- Schema structure is NOT copied (safer for PII migrations)
- Column names must match or be explicitly handled
- Use `--keep-dump` carefully (dump contains raw data)
- Safe mode temporarily adds columns - verify they're removed
- Audit trail shows exact columns being copied

## Limitations

- Large BLOBs may consume significant disk space
- SQL dump approach is I/O intensive
- Network speed affects performance
- Some MySQL-specific features require manual handling
- Data-only mode requires compatible column names (safe mode helps with this)
- Safe mode converts mismatched columns to TEXT NULL (may lose data type info)

## Examples

### Full Setup with Config

```bash
# Create config
cat > db_config.json << 'EOF'
{
  "source": {
    "host": "prod-db.example.com",
    "port": 3306,
    "user": "admin",
    "password": "prod_password",
    "database": "prod_db"
  },
  "target": {
    "host": "dev-db.example.com",
    "port": 3306,
    "user": "admin",
    "password": "dev_password",
    "database": "dev_db"
  }
}
EOF

# Run copy
python3 db_copy.py --config db_config.json

# Copy specific tables
python3 db_copy.py --config db_config.json --tables users clients

# Keep dump for inspection
python3 db_copy.py --config db_config.json --keep-dump
```

### Data-Only Examples

```bash
# Full database data-only copy
python3 db_copy.py --config db_config.json --data-only

# Safe mode with auto schema reconciliation
python3 db_copy.py --config db_config.json --data-only-safe

# Specific tables in safe mode
python3 db_copy.py --config db_config.json --data-only-safe --tables users orders

# Safe mode but keep temporary columns
python3 db_copy.py --config db_config.json --data-only-safe --keep-temp-cols

# With SSH and safe mode
python3 db_copy.py \
  --source-host prod-db.internal \
  --source-user dbuser \
  --source-password dbpass \
  --source-database mydb \
  --source-ssh-host bastion.example.com \
  --source-ssh-user ubuntu \
  --source-ssh-key ~/.ssh/prod_key \
  --target-host localhost \
  --target-user root \
  --target-password rootpass \
  --target-database mydb \
  --data-only-safe
```
