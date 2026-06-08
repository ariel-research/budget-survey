# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask research application for studying budget allocation preferences. Users allocate 100 units across subjects, then choose preferences between algorithmically generated comparison pairs. Data is used to validate utility models for the paper "What Are People's Actual Utility Functions in Budget Aggregation?" (AAMAS GAIW 2026).

This is an open-source project with a single maintainer. Prefer simple, direct solutions over abstractions — a function is better than a class, a module is better than a framework. Don't introduce patterns for hypothetical future contributors.

## Commands

### Running the Application

```bash
# Docker (recommended)
./scripts/deploy.sh dev                              # Start everything
docker compose -f docker-compose.dev.yml logs -f app # View logs
docker compose -f docker-compose.dev.yml exec app bash # Shell access
docker compose -f docker-compose.dev.yml down        # Stop

# Local
python app.py                                        # Runs on port 5001
```

### Testing

```bash
# Local
pytest                                               # Run all tests
pytest tests/services/                               # Test strategies only
pytest tests/api/                                    # Test API endpoints
pytest tests/services/pair_generation/test_rank_strategies.py  # Single test file

# In Docker
docker compose -f docker-compose.dev.yml exec app pytest
```

### Linting & Formatting

```bash
ruff check .          # Lint (uses pyproject.toml config)
ruff format .         # Format
black .               # Format (also configured in pyproject.toml)
```

### Database Migrations

```bash
# Run from inside Docker (recommended)
docker compose -f docker-compose.dev.yml exec app python migrations/run_migration.py migrations/file_name.sql --host db --port 3306

# Run locally (applies to both main and test DBs by default)
python migrations/run_migration.py migrations/file_name.sql
python migrations/run_migration.py --main-only migrations/file_name.sql
python migrations/run_migration.py --test-only migrations/file_name.sql
```

Migration files: `YYYYMMDD_descriptive_name.sql`

### Analysis

```bash
python -m analysis.survey_analysis                  # Survey analysis
python -m analysis.survey_report_generator_pdf      # Generate PDF report (deprecated)
```

## Research Correctness

**This is the most critical constraint in the codebase.** The pair generation algorithms directly determine what data is collected. A silent bug in a strategy — wrong pair ordering, a biased random draw, a math error in a utility model — corrupts the research dataset without any runtime error. Published results depend on this code being correct.

Before shipping any change that touches `application/services/pair_generation/`, `application/services/algorithms/`, or `database/queries.py`:

- Verify the mathematical property the strategy is meant to test (check the docstring and the README strategy description)
- Confirm the unit tests in `tests/services/pair_generation/` cover the invariant, not just "it runs without error"
- For new strategies, test against hand-computed examples with known outputs
- The "multiples of 5, sum to 100" invariant must hold on all generated vectors — add an assertion if a new code path could break it

## Architecture

### Application Flow

1. User arrives via Panel4All panel with `userID`, `surveyID`, optional `internalID` and `lang` params
2. `@check_survey_eligibility` decorator validates user status (blacklisted/already responded)
3. User enters their ideal budget allocation (must sum to 100, all values divisible by 5)
4. `SurveyService` generates comparison pairs via a strategy loaded from `StrategyRegistry`
5. User completes pairwise comparisons with embedded awareness/attention checks
6. Results are stored in MySQL; user is redirected to Panel4All with completion code

### Key Layers

- **`app.py`**: Flask factory, blueprint registration, template filters
- **`config.py`**: `Config` / `TestConfig` classes; active survey set via `SURVEY_ID` env var
- **`application/routes/`**: Blueprints — `survey`, `dashboard`, `report`, `survey_responses`, `utils`
- **`application/services/survey_service.py`**: Orchestrates pair generation, awareness checks, submission
- **`application/services/pair_generation/`**: Strategy pattern implementations (see below)
- **`application/services/algorithms/`**: Pure math — utility models and `math_utils.py`
- **`application/translations.py`**: All UI strings in Hebrew + English; never hardcode strings
- **`database/queries.py`**: All DB access via raw SQL (`execute_query` helper)
- **`analysis/`**: Standalone scripts for post-hoc research analysis

### Pair Generation Strategy System

New strategies extend `PairGenerationStrategy` (in `base.py` — **do not modify this file**) and must be registered in `application/services/pair_generation/__init__.py`.

**For new rank-based strategies**: extend `GenericRankStrategy` (`generic_rank_strategy.py`) and compose two `UtilityModel` instances. Metrics live in `application/services/algorithms/utility_models.py` and **must always return higher-is-better** (distances returned as negatives).

**StrategyRegistry** (singleton) maps strategy name strings to classes. The survey's `pair_generation_config` JSON column specifies which strategy and params to use.

### Database Schema (MySQL)

- `stories`: Survey topics with `subjects` JSON (the budget categories), multilingual `title`/`description`
- `surveys`: Links to a story; holds `pair_generation_config` JSON specifying strategy + params
- `survey_responses`: One per user per survey; stores `optimal_allocation` JSON, completion/attention flags
- `comparison_pairs`: Each pair a user saw, with their choice and strategy metadata

Active survey is controlled by `SURVEY_ID` in `config.py` (overridable via env var).

### Multilingual / RTL

Language is set per-request via `?lang=he|en`. Default is Hebrew (`he`). Always test UI changes for both RTL (Hebrew) and LTR (English) layouts. All strings go through `application/translations.py`.

### Important Constraints

- **Budget multiples of 5**: All allocation vectors must be integers divisible by 5 and sum to 100. Verify any new algorithm or UI change respects this.
- **Raw SQL only**: No ORM. All queries go through `database/queries.py`.
- **`UnsuitableForStrategyError`**: Raise this (not a generic error) when a user's ideal vector doesn't satisfy a strategy's requirements (e.g., contains zeros when strategy requires all-positive).
- **PDF generation** (`survey_report_generator_pdf.py`): Deprecated — do not extend.
- **`dashboard_OLD.py` / `surveys_overview_OLD.html`**: Legacy files, do not modify.

### Security

- **`userID` is untrusted external input** from Panel4All query params. It is used as a DB primary key — always pass it through parameterized queries via `execute_query`, never string-interpolated into SQL.
- **`internalID` param** lets callers switch the active survey. This is intentional (demo/research use), not a bug. Do not add server-side restrictions without understanding this.
- **Dashboard has no authentication** — this is a deliberate design decision for an internal research tool. Do not add auth without discussing it first; do not expose the dashboard URL publicly.
- **Jinja2 auto-escaping** is active for all templates. Never use `| safe` on user-supplied data.
