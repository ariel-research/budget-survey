# Migration Scripts

This directory contains database migration scripts for the Budget Survey application.

## Running Migrations

To run a migration script:

1. Ensure your environment variables are properly configured in the `.env` file at the project root
2. Run the migration script using:

```bash
python migrations/run_migration.py migrations/migration_filename.sql
```

**Important**: By default, migrations are applied to **both** the main database (`survey`) and test database (`test_survey`) to keep them in sync.

For example, to run the unaware users migration:

```bash
python migrations/run_migration.py migrations/20250511_retroactive_unaware_users.sql
```

### Migration Options

You can control which databases the migration runs on:

```bash
# Run on both databases (default behavior)
python migrations/run_migration.py migrations/migration_filename.sql

# Run only on main database
python migrations/run_migration.py --main-only migrations/migration_filename.sql

# Run only on test database
python migrations/run_migration.py --test-only migrations/migration_filename.sql
```

### Docker Database Connections

#### Option 1: Running from inside Docker container (Recommended)
If you're using the Docker setup, run migrations from inside the app container:

```bash
docker compose -f docker-compose.dev.yml exec app python migrations/run_migration.py migrations/migration_filename.sql --host db --port 3306
```

For example:
```bash
docker compose -f docker-compose.dev.yml exec app python migrations/run_migration.py migrations/20250806_add_transitivity_analysis.sql --host db --port 3306
```

**Important**: Use `--host db` (Docker service name) and `--port 3306` (container port), not the host-mapped port.

#### Option 2: Running from host machine
If you need to run migrations from outside the Docker container (e.g., for external database connections), use the host-mapped port:

```bash
python migrations/run_migration.py migrations/migration_filename.sql --host localhost --port 3307
```

This is useful when connecting to the MySQL server from the host machine via the mapped port.

## Migration Naming Convention

Migration files follow the timestamp naming convention:

`YYYYMMDD_descriptive_name.sql`

Where:
- `YYYYMMDD` is the date the migration was created
- `descriptive_name` describes what the migration does
- `.sql` is the file extension for SQL migrations

## Available Migrations

In chronological order:

- `20250101_add_pair_generation_config.sql` - Adds a JSON column for storing pair generation configuration to the surveys table
- `20250123_add_strategy_columns.sql` - Adds strategy columns to comparison_pairs table to track which strategy generated each option
- `20250216_add_attention_check_column.sql` - Adds attention_check_failed column to survey_responses table
- `20250401_add_stories_table.sql` - Creates stories table and refactors surveys table to use story references
- `20250501_add_user_blacklist.sql` - Adds blacklisting columns to users table for handling users who fail attention checks
- `20250511_retroactive_unaware_users.sql` - Retroactively blacklists users who failed attention checks but weren't previously marked as blacklisted
- `20250514_add_weighted_vector_views.sql` - Creates SQL views for analyzing user preferences for weighted vector strategies
- `20250616_add_option_differences.sql` - Adds option1_differences and option2_differences columns to comparison_pairs table for storing vector differences (used by cyclic shift strategy)
- `20250806_add_transitivity_analysis.sql` - Adds transitivity_analysis JSON column to survey_responses table for storing transitivity metrics from extreme vectors strategy analysis
- `20250907_add_strategy_instructions.sql` - Adds pair_instructions JSON column to surveys table for storing custom strategy instructions in Hebrew and English
