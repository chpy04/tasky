# Migrations

Database migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

## Setup

Alembic is initialized in this directory. The `env.py` file imports all
SQLAlchemy models so Alembic can auto-generate migration scripts by
comparing the current schema to the models.

## Common commands

```bash
# Generate a new migration after changing models
uv run alembic revision --autogenerate -m "describe the change"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one migration
uv run alembic downgrade -1
```

## TODO

- Initialize Alembic (`alembic init`) and wire `env.py` to import all models
- Create the initial migration covering all tables in the current schema
