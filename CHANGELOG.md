# Changelog

## [Unreleased]

## [0.6.1] - 2025-02-26
### Changed
- improve CHANGELOG.md formatting

## [0.6.0] - 2025-02-26
### Added
- rename `calculateroleset` to `set-role` for better clarity

## [0.5.0] - 2025-02-26
### Added
- Pagination to model select view.

## [0.4.1] - 2025-02-26
### Fixed
- Preview calculate-workflow ephemeral is now being properly deleted after confirmation.

## [0.4.0] - 2025-02-26
### Added
- calculate-workflow updates:
    - Finish button is now Continue button.
    - Models are being loaded from file,
    - `Confirm & Post` / `Cancel` buttons,
    - Calculate preview before confirming it.

## [0.3.0] - 2025-02-26
### Added
- new commands:
    - `remove-bonus-rule`: Remove a bonus rule for a specific revenue range,
    - `remove-period`: Remove a selected period from configuration,
    - `remove shift`: Remove a shift configuration,
    - `remove-role`: Remove a role's percentage configuration.

## [0.2.0] - 2025-02-26
### Added
- correct version bump
    - instead of v0.1.9 bumped to v0.2.0

## [0.1.9] - 2025-02-26
### Added
- clean code and new commands:
    - `set-model`: admin command that sets new model name,
    - `remove-model`: removes a model,
    - `list-models`: gets list of all available models.

## [0.1.8] - 2025-02-25
### Added
- finalize embedded result for calculate-workflow

## [0.1.7] - 2025-02-25
### Added
- model selection to the calculate-workflow

## [0.1.6] - 2025-02-25
### Added
- revenue input to the calculate-workflow

## [0.1.5] - 2025-02-25
### Added
- role selection to the calculate-workflow

## [0.1.4] - 2025-02-25
### Added
- shift selection to the calculate-workflow

## [0.1.3] - 2025-02-25
### Added
- period selection to the calculate-workflow

## [0.1.2] - 2025-02-25
### Added
- `calculate-workflow` command that will initiate interactive workflow

## [0.1.1] - 2025-02-25
### Added
- `cogs/calculator_slash.py` for calculator interaction workflow

## [0.1.0] - 2025-02-25
### Added
- `main.py` system remodeled
    - bug fixes,
    - clean code.
    - remodeled functions now being used instead.

## [0.0.22] - 2025-02-25
### Added
- add `cogs/reports.py` for reporting functionality cogs.
- new report command:
    - summary: Generate a summary report for all earnings in a period.

## [0.0.21] - 2025-02-25
### Added
- `cogs/calculator.py` for calculator command cogs.
- new calculator commands:
    - `calculate`: Calculate earnings based on revenue, role, and shift,
    - `total`: Calculate total earnings for a period and optional date range.

## [0.0.20] - 2025-02-25
### Added
- new admin commands:
    - `calculateroleset`: set a role's percentage cut,
    - `calculateshiftset`: add a valid shift name,
    - `calculateperiodset`: add a valid period name,
    - `calculatebonus`: set a bonus rule for a revenue range,
    - `calculateroleslist`: list all configured roles and their percentages,
    - `calculateshiftslist`: list all configured shifts,
    - `calculateperiodslist`: list all configured periods,
    - `calculatebonuslist`: list all configured bonus rules.

## [0.0.19] - 2025-02-25
### Added
- `cogs/admin.py` for admin commands cogs

## [0.0.18] - 2025-02-25
### Added
- `config/settings.py` configuration module

## [0.0.17] - 2025-02-25
### Added
- implemented `get_total_earnings` function in `calculations.py` for calculating total earnings from a list of earnings data

## [0.0.16] - 2025-02-25
### Added
- implemented `calculate_earnings` function in `calculations.py` for calculating all earnings values

## [0.0.15] - 2025-02-25
### Added
- implemented `find_applicable_bonus` function in `calculations.py` for finding the applicable bonus based on revenue and rules

## [0.0.14] - 2025-02-25
### Added
- implemented `calculate_revenue_share` function in `calculations.py` for calculating employee's cut based on gross revenue and role percentage

## [0.0.13] - 2025-02-24
### Added
- `utils/calculations.py` for monetary calculations

## [0.0.12] - 2025-02-24
### Added
- implemented v`alidate_bonus_rules` function in `validators.py` for validation of bonus rules for consistency and overlaps

## [0.0.11] - 2025-02-24
### Added
- implemented `validate_period` function in `validators.py` for validation and finding a period by name (case-insensitive)

## [0.0.10] - 2025-02-24
### Added
- implemented `validate_shift` function in `validators.py` for validation and finding a shift by name (case-insensitive)

## [0.0.9] - 2025-02-24
### Added
- implemented `validate_date_format` function in `validators.py` for validation if a string matches the expected date format

## [0.0.8] - 2025-02-24
### Added
- implemented `validate_percentage` function in `validators.py` for percentage validation if value is between 0-100

## [0.0.7] - 2025-02-24
### Added
- implemented `parse_money` function in `validators.py` for parsing a monetary value to Decimal with proper validation

## [0.0.6] - 2025-02-24
### Added
- `utils/validators.py` for monetary calculations

## [0.0.5] - 2025-02-24
### Added
- implemented `save_json` function in `file_handlers.py` for saving JSON files

## [0.0.4] - 2025-02-24
### Added
- implemented `load_json` function in `file_handlers.py` for reading JSON files

## [0.0.3] - 2025-02-24
### Added
- `utils/file_handlers.py` for future file operations

## [0.0.2] - 2025-02-24
### Added
- logging for better debugging and monitoring

## [0.0.1] - 2025-02-24
### Added
- `.env` for secure token management