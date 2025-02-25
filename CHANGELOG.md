# Changelog

## [Unreleased]

## [0.0.18] - 2025-02-24
### Added
- config/settings.py configuration module

## [0.0.17] - 2025-02-24
### Added
- implemented get_total_earnings function in calculations.py for calculating total earnings from a list of earnings data

## [0.0.16] - 2025-02-24
### Added
- implemented calculate_earnings function in calculations.py for calculating all earnings values

## [0.0.15] - 2025-02-24
### Added
- implemented find_applicable_bonus function in calculations.py for finding the applicable bonus based on revenue and rules

## [0.0.14] - 2025-02-24
### Added
- implemented calculate_revenue_share function in calculations.py for calculating employee's cut based on gross revenue and role percentage

## [0.0.13] - 2025-02-24
### Added
- utils/calculations.py for monetary calculations

## [0.0.12] - 2025-02-24
### Added
- implemented validate_bonus_rules function in validators.py for validation of bonus rules for consistency and overlaps

## [0.0.11] - 2025-02-24
### Added
- implemented validate_period function in validators.py for validation and finding a period by name (case-insensitive)

## [0.0.10] - 2025-02-24
### Added
- implemented validate_shift function in validators.py for validation and finding a shift by name (case-insensitive)

## [0.0.9] - 2025-02-24
### Added
- implemented validate_date_format function in validators.py for validation if a string matches the expected date format

## [0.0.8] - 2025-02-24
### Added
- implemented validate_percentage function in validators.py for percentage validation if value is between 0-100

## [0.0.7] - 2025-02-24
### Added
- implemented parse_money function in validators.py for parsing a monetary value to Decimal with proper validation

## [0.0.6] - 2025-02-24
### Added
- utils/validators.py for monetary calculations

## [0.0.5] - 2025-02-24
### Added
- implemented save_json function in file_handlers.py for saving JSON files

## [0.0.4] - 2025-02-24
### Added
- implemented load_json function in file_handlers.py for reading JSON files

## [0.0.3] - 2025-02-24
### Added
- utils/file_handlers.py for future file operations

## [0.0.2] - 2025-02-24
### Added
- logging for better debugging and monitoring

## [0.0.1] - 2025-02-24
### Added
- .env for secure token management