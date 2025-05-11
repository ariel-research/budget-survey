# Migration Scripts

This directory contains database migration scripts for the Budget Survey application.

## Running Migrations

To run a migration script:

1. Ensure your environment variables are properly configured in the `.env` file at the project root
2. Run the migration script using:

```bash
python migrations/run_migration.py migrations/migration_filename.sql
```

For example, to run the unaware users migration:

```bash
python migrations/run_migration.py migrations/20250511_retroactive_unaware_users.sql
```

### Docker Database Connections

If you're using MySQL in a Docker container with port mapping, you can specify the host and port directly:

```bash
python migrations/run_migration.py migrations/20250511_retroactive_unaware_users.sql --host localhost --port 3307
```

This is useful when the MySQL server is running on a non-standard port (e.g., Docker mapped port).

## Migration Naming Convention

Migration files follow the timestamp naming convention:

`YYYYMMDD_descriptive_name.sql`

Where:
- `YYYYMMDD` is the date the migration was created
- `descriptive_name` describes what the migration does
- `.sql` is the file extension for SQL migrations

## Available Migrations

- `20250511_retroactive_unaware_users.sql` - Retroactively blacklists users who failed attention checks but weren't previously marked as blacklisted 