# Database Migrations

This directory contains database migration files managed by Alembic.

## Quick Start

```bash
# Apply all pending migrations
./scripts/migrate.sh upgrade

# Rollback last migration
./scripts/migrate.sh downgrade

# Create new migration
./scripts/migrate.sh create "description"

# View migration history
./scripts/migrate.sh history
```

## Structure

- `env.py` - Migration environment configuration
- `script.py.mako` - Template for new migration files
- `versions/` - Contains all migration version files

## Learn More

See [MIGRATIONS.md](../MIGRATIONS.md) in the project root for complete documentation.
