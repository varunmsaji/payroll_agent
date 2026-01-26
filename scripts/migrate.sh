#!/bin/bash
# Migration helper script for common Alembic operations

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_usage() {
    echo "Usage: $0 {upgrade|downgrade|create|history|current|stamp}"
    echo ""
    echo "Commands:"
    echo "  upgrade [revision]    Apply migrations (default: head)"
    echo "  downgrade [count]     Rollback migrations (default: -1)"
    echo "  create \"description\"   Create a new migration"
    echo "  history               Show migration history"
    echo "  current               Show current migration version"
    echo "  stamp head            Mark database as current (no changes)"
    echo ""
    echo "Examples:"
    echo "  $0 upgrade            # Apply all pending migrations"
    echo "  $0 downgrade -2       # Rollback 2 migrations"
    echo "  $0 create \"add user photo column\""
    echo "  $0 history"
    exit 1
}

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable is not set${NC}"
    echo "Set it in your .env file or export it:"
    echo "  export DATABASE_URL='postgresql://user:pass@host:5432/dbname'"
    exit 1
fi

case "$1" in
    upgrade)
        REVISION=${2:-head}
        echo -e "${GREEN}Applying migrations to: $REVISION${NC}"
        alembic upgrade "$REVISION"
        echo -e "${GREEN}✓ Migrations applied successfully${NC}"
        ;;
    
    downgrade)
        COUNT=${2:--1}
        echo -e "${YELLOW}Rolling back migrations: $COUNT${NC}"
        read -p "Are you sure? This will modify the database. (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            alembic downgrade "$COUNT"
            echo -e "${GREEN}✓ Rollback completed${NC}"
        else
            echo "Cancelled"
        fi
        ;;
    
    create)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Migration description required${NC}"
            echo "Usage: $0 create \"description\""
            exit 1
        fi
        echo -e "${GREEN}Creating new migration: $2${NC}"
        alembic revision --autogenerate -m "$2"
        echo -e "${GREEN}✓ Migration created${NC}"
        echo -e "${YELLOW}⚠ Please review the generated migration file!${NC}"
        ;;
    
    history)
        echo -e "${GREEN}Migration history:${NC}"
        alembic history --verbose
        ;;
    
    current)
        echo -e "${GREEN}Current migration version:${NC}"
        alembic current
        ;;
    
    stamp)
        REVISION=${2:-head}
        echo -e "${YELLOW}Marking database as: $REVISION (no schema changes)${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            alembic stamp "$REVISION"
            echo -e "${GREEN}✓ Database stamped${NC}"
        else
            echo "Cancelled"
        fi
        ;;
    
    *)
        print_usage
        ;;
esac
