# Database Migrations Guide

## Overview

This project uses **Alembic** for database migrations, providing version control for your database schema with full rollback capabilities.

---

## Quick Start

### Apply Pending Migrations
```bash
./scripts/migrate.sh upgrade
```

### Rollback Last Migration
```bash
./scripts/migrate.sh downgrade
```

### Create New Migration
```bash
./scripts/migrate.sh create "add employee photo column"
```

### View Migration History
```bash
./scripts/migrate.sh history
```

---

## What Are Migrations?

Migrations are **version-controlled database schema changes**. Each migration is a Python file with two functions:
- `upgrade()` - Apply the change
- `downgrade()` - Rollback the change

Example:
```python
def upgrade():
    op.add_column('employees', sa.Column('photo_url', sa.String(255)))

def downgrade():
    op.drop_column('employees', 'photo_url')
```

---

## Common Operations

### 1. Creating a New Migration

**When you need to change the database schema:**

```bash
# Method 1: Auto-generate from model changes (recommended)
./scripts/migrate.sh create "add employee photo column"

# Method 2: Manual (advanced)
alembic revision -m "description"
```

**Auto-generate workflow:**
1. Modify `app/database/models.py`
2. Run migrate script
3. Review generated file in `migrations/versions/`
4. Test locally
5. Commit to Git

### 2. Applying Migrations

```bash
# Apply all pending migrations
./scripts/migrate.sh upgrade

# Apply to specific version
alembic upgrade abc123

# Apply just one migration
alembic upgrade +1
```

### 3. Rolling Back

```bash
# Rollback last migration
./scripts/migrate.sh downgrade

# Rollback multiple migrations
./scripts/migrate.sh downgrade -3

# Rollback to specific version
alembic downgrade abc123

# Rollback all migrations (dangerous!)
alembic downgrade base
```

### 4. Checking Status

```bash
# See current version
./scripts/migrate.sh current

# See full history
./scripts/migrate.sh history

# Check pending migrations
alembic current
alembic heads
```

---

## Detailed Workflow

### Scenario 1: Adding a New Column

**Goal**: Add `photo_url` to employees table

1. **Update the model**:
   ```python
   # app/database/models.py
   class Employee(Base):
       __tablename__ = "employees"
       # ... existing columns ...
       photo_url = Column(String(255))  # ← NEW
   ```

2. **Generate migration**:
   ```bash
   ./scripts/migrate.sh create "add employee photo_url column"
   ```

3. **Review generated file**:
   ```bash
   # migrations/versions/abc123_add_employee_photo_url_column.py
   ```
   Check that it detected the change correctly.

4. **Test locally**:
   ```bash
   ./scripts/migrate.sh upgrade
   # Verify in database
   ./scripts/migrate.sh downgrade -1
   # Verify rollback worked
   ./scripts/migrate.sh upgrade
   ```

5. **Commit**:
   ```bash
   git add migrations/ app/database/models.py
   git commit -m "Add photo_url to employees"
   git push
   ```

### Scenario 2: Modifying a Column

**Goal**: Change `email` from nullable to non-nullable

1. **Update model**:
   ```python
   email = Column(String, nullable=False)  # was nullable=True
   ```

2. **Generate & review**:
   ```bash
   ./scripts/migrate.sh create "make employee email required"
   ```

3. **Important**: Make sure existing data won't break!
   - Check for NULL emails in database
   - Add data migration if needed

4. **Test and commit**

### Scenario 3: Creating a New Table

1. **Create model** in `app/database/models.py`:
   ```python
   class Department(Base):
       __tablename__ = "departments"
       id = Column(Integer, primary_key=True)
       name = Column(String, nullable=False)
       created_at = Column(DateTime, server_default=func.now())
   ```

2. **Generate migration**:
   ```bash
   ./scripts/migrate.sh create "create departments table"
   ```

3. **Test and commit**

---

## Production Workflow

### Before Deploying

1. **Test in staging**:
   ```bash
   # On staging server
   git pull
   ./scripts/migrate.sh upgrade
   # Test application
   ```

2. **Backup production database**:
   ```bash
   # Using Supabase dashboard or CLI
   supabase db dump -f backup.sql
   ```

3. **Deploy to production**:
   ```bash
   # On production server
   git pull
   ./scripts/migrate.sh upgrade
   ```

4. **Verify**:
   - Check logs
   - Test critical endpoints
   - Monitor for errors

### If Something Goes Wrong

```bash
# Rollback immediately
./scripts/migrate.sh downgrade -1

# Or restore from backup
psql $DATABASE_URL < backup.sql
```

---

## Team Collaboration

### Avoiding Conflicts

**Problem**: Two developers create migrations at the same time

**Solution**:
1. Always pull before creating migrations
2. If conflict occurs, use `alembic merge`
3. Communicate with team about schema changes

### Best Practices

1. **One change per migration** - Don't mix unrelated changes
2. **Descriptive names** - `add_user_avatar` not `update_users`
3. **Review carefully** - Check autogenerated migrations
4. **Test rollback** - Always verify downgrade works
5. **Backup first** - Especially in production

---

## Troubleshooting

### Migration Fails

```bash
# Check what went wrong
alembic current
alembic history

# Fix the issue, then:
./scripts/migrate.sh downgrade -1  # if partially applied
# Fix migration file
./scripts/migrate.sh upgrade
```

### "Can't locate revision" Error

```bash
# Database and code are out of sync
# Option 1: Stamp database (if you know the  correct version)
./scripts/migrate.sh stamp head

# Option 2: Check history and manually fix
alembic history
alembic stamp abc123
```

### Auto-generate Detects Too Many Changes

```bash
# Clean up:
1. Make sure DATABASE_URL points to correct database
2. Ensure all models are imported in models.py
3. Check if you modified models accidentally

# Generate again
./scripts/migrate.sh create "actual change description"
```

### Supabase SSL Error

Add to your `.env`:
```
DATABASE_URL=postgresql://user:pass@db.xxx.supabase.co:5432/postgres?sslmode=require
```

---

## Advanced Operations

### Manual Migrations

For complex data migrations or custom SQL:

```bash
# Create empty migration
alembic revision -m "migrate user data"
```

Edit the file:
```python
def upgrade():
    # Custom SQL or Python code
    op.execute("UPDATE employees SET status='active' WHERE status IS NULL")

def downgrade():
    # Reverse operation
    op.execute("UPDATE employees SET status=NULL WHERE status='active'")
```

### Branching and Merging

If your team creates parallel migrations:

```bash
# Create merge migration
alembic merge -m "merge migrations" head1 head2
```

### Offline SQL Generation

Generate SQL without connecting to database:

```bash
alembic upgrade head --sql > migration.sql
# Review and run manually
```

---

## CI/CD Integration

The migration validation is already configured in `.github/workflows/ci.yml`.

**What it does**:
- Validates migration files on every push
- Checks for conflicts
- Verifies rollback works

**Manual CI run**:
```bash
# In CI environment
pip install -r requirements.txt
alembic check  # Verify migrations are valid
```

---

## File Structure

```
payroll_backend/
├── migrations/
│   ├── alembic.ini          # Configuration
│   ├── env.py               # Environment setup
│   ├── script.py.mako       # Template for new migrations
│   └── versions/            # Migration files
│       ├── 001_initial_schema.py
│       ├── 002_add_photo_url.py
│       └── 003_create_departments.py
├── app/database/
│   ├── base.py              # SQLAlchemy engine
│   ├── models.py            # Table definitions
│   └── connection.py        # Raw SQL connection (still works)
└── scripts/
    └── migrate.sh           # Helper script
```

---

## FAQ

**Q: Do I have to use ORM queries now?**
A: No! You can still use raw SQL with `psycopg2`. Models are only for migrations.

**Q: What if I want to modify production directly?**
A: Don't! Always use migrations for schema changes.

**Q: Can I rollback after deploying?**
A: Yes, but be careful with data loss. Always backup first.

**Q: How do I see what changed between versions?**
A: Check the migration files in `migrations/versions/`

**Q: Can I edit a migration after it's applied?**
A: No, create a new migration to fix it.

---

## Cheat Sheet

| Command | Description |
|---------|-------------|
| `./scripts/migrate.sh upgrade` | Apply all pending migrations |
| `./scripts/migrate.sh downgrade -1` | Rollback last migration |
| `./scripts/migrate.sh create "desc"` | Create new migration |
| `./scripts/migrate.sh history` | Show all migrations |
| `./scripts/migrate.sh current` | Show current version |
| `alembic heads` | Show latest migration |
| `alembic branches` | Show branches (if any) |
| `alembic stamp head` | Mark as current (no changes) |

---

## Support

For more information:
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Check migration files for examples

---

**Remember**: 
- ✅ Always test locally first
- ✅ Backup before production changes
- ✅ Review autogenerated migrations
- ✅ Commit migrations with code changes
