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

## How It Works

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

## Common Scenarios

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

## Performance Tips

1. **Large Databases**: For multi-gigabyte databases, consider:
   - Running on a machine close to both servers
   - Using a persistent SSH connection
   - Keeping `--keep-dump` to preserve a backup

2. **Network Optimization**:
   - SSH via LAN is faster than over internet
   - Consider gzip compression if network-bound
   - Run during off-peak hours

3. **Database Optimization**:
   - Specific table copy is faster than full database
   - Indexes are included automatically
   - Foreign key constraints are preserved

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use SSH key authentication** instead of passwords when possible
3. **Secure private keys**: `chmod 600 ~/.ssh/id_rsa`
4. **Use strong passwords** for database users
5. **Restrict network access** to database servers
6. **Use environment-specific credentials** (dev/prod/staging)
7. **Review SQL dump files** if `--keep-dump` is used

## Limitations

- Large BLOBs may consume significant disk space
- SQL dump approach is I/O intensive
- Network speed affects performance
- Some MySQL-specific features require manual handling

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
