# Installation Guide

## Quick Start

### Install from PyPI (Recommended)

```bash
pip install db-copy-mysql
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/harish2704/db-copy-mysql.git
cd db-copy-mysql

# Install in development mode
pip install -e .

# Or install from built distribution
python -m build
pip install dist/db_copy_mysql-1.0.0-py3-none-any.whl
```

## System Requirements

Before installing, ensure you have the following system tools:

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
```

**macOS (with Homebrew):**
```bash
brew install openssh mysql-client
```

**CentOS/RHEL:**
```bash
sudo yum install openssh-clients mysql
```

## Usage

After installation, the `db-copy-mysql` command will be available globally:

```bash
# Show help
db-copy-mysql --help

# Show sample configuration
db-copy-mysql --sample-config

# Copy using config file
db-copy-mysql --config config.json

# Direct connection
db-copy-mysql \
  --source-host source-db.com \
  --source-user root \
  --source-password pass \
  --source-database mydb \
  --target-host target-db.com \
  --target-user root \
  --target-password pass \
  --target-database mydb
```

## Development

### Install Development Dependencies

```bash
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Build Package

```bash
python -m build
```

This creates both source distribution (.tar.gz) and wheel (.whl) files in the `dist/` directory.

## Troubleshooting

### Command Not Found

If `db-copy-mysql` command is not found after installation:

1. Check if pip installed to user directory:
   ```bash
   echo $PATH
   ```
   The command should be in `~/.local/bin/` which should be in your PATH.

2. Add to PATH if needed:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. Make it permanent by adding to your shell profile:
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Permission Issues

If you get permission errors during installation:

```bash
# Use user installation
pip install --user db-copy-mysql

# Or use virtual environment
python -m venv venv
source venv/bin/activate
pip install db-copy-mysql
```

### Missing System Tools

If you get errors about missing `ssh`, `mysqldump`, or `mysql`:

Install the required system packages as shown in the System Requirements section above.