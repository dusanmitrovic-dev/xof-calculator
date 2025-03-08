# Changelog

## [Unreleased]

## [0.89.0] - 2025-03-08
### Rollback
- Rollback to stable `v0.86.0` release.

## [0.87.0] - 2025-03-08
### Changed
- `view-earnings` functions merged with new `as_table` parameter.

## [0.86.0] - 2025-03-08
### Changed
- Enhance `view-earnings-table` command to support multiple recipients and improved error handling.

## [0.85.0] - 2025-03-08
### Changed
`view-earnings-admin`:
- Add send_to, range_from, and range_to parameters
- Implement date filtering and recipient management

## [0.84.0] - 2025-03-08
### Changed
- feat(calculator_slash): enhance `view-earnings-admin-table` command with improved descriptions and recipient handling.

## [0.83.0] - 2025-03-08
### Added
- Added `range_from` and `range_to` parameters for filtering earnings by date.
- Implemented `send_to` functionality to send reports via DM to users/roles.
- Improved earnings display with separators and additional fields.
- Enhanced export handling with better error messages.

## [0.82.0] - 2025-03-08
### Added
- Updated new functionalities for `view-earnings-admin-table` command.

## [0.81.0] - 2025-03-08
### Added
- `range_from` and `range_to` parameters
- send_to: that will send report to the user DM
- new export formats for `view-earnings-table`
- new command `view-earnings-table`

## [0.80.2] - 2025-03-08
### Fixed
- Fixed export zip functionality with better base naming.

## [0.80.1] - 2025-03-07
### Fixed
Fix bug where view-earnings command did not display

Resolved issue where both `view-earnings` and `view-earnings-table` had the same method name, 
causing the `/view-earnings` command to not register.
This bug was introduced while adding the `/view-earnings-table` feature.

## [0.80.0] - 2025-03-07
### Changed
- `view-earnings` command changed to `view-earnings-table`,
- `view-earnings-admin` command changed to `view-earnings-table-admin`,
- export options JSON. Excel, PDF, PNG Chart, ZIP Archive.

## [0.79.0] - 2025-03-07
### Changed
- `view-earnings`,
- `view-earnings-admin`,
they can now also export data to formats CSV and TXT.

## [0.78.0] - 2025-03-07
### Changed
- Calculate slash preview and finalize field display.

## [0.77.0] - 2025-03-07
### Changed
- Remove hours for commission views,
- Remove net revenue in hourly views.

## [0.76.0] - 2025-03-07
### Changed
These functions now have full ephemeral support logic:
- `remove-role`,
- `list-roles`.

## [0.75.0] - 2025-03-07
### Changed
- `help` slash command now displays `toggle-ephemeral`,
- `set-role` has fully ephemeral support.

## [0.74.0] - 2025-03-07
### Changed
- `reset-config` now uses helper reset functions

## [0.73.0] - 2025-03-07
### Added
- `reset-display-config`,
- `restore-display-config`.
### Changed
- `reset-config` now resets display settings as well.

## [0.72.0] - 2025-03-07
### Added
- `toggle-ephemeral`.
### Changed
- `set-period` is now fully ephemeral.

## [0.71.0] - 2025-03-07
### Added
- New command `restore-compensation-backup`.

## [0.70.0] - 2025-03-07
### Changed
- `clear-compensation` renamed to `reset-compensation-config`.

## [0.69.0] - 2025-03-07
### Added
- New command `clear-compensation`.

## [0.68.0] - 2025-03-07
### Changed
- `reset-config` updated to reset compensation settings as well.

## [0.67.0] - 2025-03-06
### Changed
- Remove loggers from preview method.

## [0.66.0] - 2025-03-06
### Changed
- Most of admin command messages are ephemeral now,
- `/calculate workflow` will only show roles that user has.

## [0.65.0] - 2025-03-06
### Added
- New `toggle-user-role-override` command.

## [0.64.0] - 2025-03-06
### Changed
- (calculator_slash): fixed role logic for commission settings,
- (admin_slash): commission commands are now admin only.

## [0.63.0] - 2025-03-06
### Changed
- (calculator_slash): compensation view now gets edited instead of staying untouched,
- (admin_slash): updated configuration commands for new `commission_settings.json` structure.

## [0.62.0] - 2025-03-06
### Added
- Second working version for preview / finalize methods with compensation and real hours input data.

## [0.61.0] - 2025-03-06
### Added
- First working version for preview with compensation and dummy 8 hours of work data.

## [0.60.0] - 2025-03-05
### Changed
- Modified `calculate_hourly_earnings` method to align with already used logic.

## [0.59.0] - 2025-03-05
### Added
- Implemented `calculate_hourly_earnings` method.

## [0.58.0] - 2025-03-05
### Added
- Compensation step to the workflow.

## [0.58.0] - 2025-03-05
### Added
- Compensation step to the workflow.

## [0.57.0] - 2025-03-05
### Added
- New commands:
    - `/set-role-commission`,
    - `/set-role-hourly`,
    - `/set-user-commission`,
    - `/set-user-hourly`,
    - `/view-commission-settings`.

## [0.56.0] - 2025-03-05
### Changed
- `view-earnings` split in two commands:
    - `view-earnings-admin` admin will see users earning entries,
    - `view-earnings` user command version.

## [0.55.0] - 2025-03-05
### Added
- changes:
    - new `help` slash command for slash commands,
    - new `view-earnings` slash command that returns 25 latest entries for earnings,
    - removed residual backup data files that were forgotten in previous versions.

## [0.54.0] - 2025-03-04
### Added
- Added confirm and cancel buttons for reset and restore commands.

## [0.53.0] - 2025-03-04
### Added
- New admin slash command `restore-models-backup`.

## [0.52.0] - 2025-03-04
### Added
- New admin slash command `reset-models-config`.

## [0.51.0] - 2025-03-04
### Fixed
- `restore-earnings-backup` command fixed, correct file path is being used.

## [0.50.0] - 2025-03-04
### Fixed
- `restore-role-backup` command fixed, correct file path is being used.

## [0.49.0] - 2025-03-04
### Fixed
- `restore-period-backup` command fixed, correct file path is being used.

## [0.48.0] - 2025-03-04
### Fixed
- `restore-shift-backup` command fixed, correct file path is being used.

## [0.47.0] - 2025-03-04
### Fixed
- `restore-bonus-backup` command fixed, correct file path is being used.

## [0.46.0] - 2025-03-04
### Fixed
- Indentation on line 23 in `admin_slash.py.

## [0.45.0] - 2025-03-04
### Added
New admin slash commands:
- Reset Individual Config Files:
    - `reset-shift-config`,
    - `reset-period-config`,
    - `reset-role-config`,
    - `reset-bonus-config`,
    - `reset-earnings-config`,
- Restore Individual Backup Files:
    - `restore-shift-backup`,
    - `restore-period-backup`,
    - `restore-role-backup`,
    - `restore-bonus-backup`,
    - `restore-earnings-backup`.

## [0.44.0] - 2025-03-04
### Rollback
- Rolled back to `v0.34.0` due to unnecessary error handling that already exists in `main.py`,
- removing unnecessary `v0.34.0` error handling,
- using new command names from newer versions,
- fixing up todo tasks to follow the rollback.

## [0.43.0] - 2025-03-03
### Changed
- `set-period` command has better error handling now.

## [0.42.0] - 2025-03-03
### Changed
- `remove-shift` command has better error handling now.

## [0.41.0] - 2025-03-03
### Changed
- `set-shift` command has better error handling now.

## [0.40.0] - 2025-03-03
### Changed
- `set-shift` command has better error handling now.

## [0.40.0] - 2025-03-03
### Changed
- `remove-role` command has better error handling now.

## [0.39.0] - 2025-03-03
### Changed
- `set-role` command has better error handling now.

## [0.38.0] - 2025-03-03
### Changed
- `export-earnings-json` command usage updated to follow new command name.

## [0.37.0] - 2025-03-03
### Changed
- `admin-export-earnings-json` command renamed to `export-earnings-json` for simplicity.

## [0.36.0] - 2025-03-03
### Changed
- `export-earnings-csv` command usage updated to follow new command name.

## [0.35.0] - 2025-03-03
### Changed
- `admin-export-earnings-csv` command renamed to `export-earnings-csv` for simplicity.

## [0.34.0] - 2025-03-03
### Changed
- `toggle-average` command has better error handling now.

## [0.33.0] - 2025-03-03
### Changed
- `clear-earnings` command message updated.

## [0.32.1] - 2025-03-03
### Removed
- `set-model` duplicate method slash command.

## [0.32.0] - 2025-03-02
### Added
- `set-model` success and failure cases set.

## [0.31.0] - 2025-03-02
### Added
- `set-model` command is saving properly to file.

## [0.30.0] - 2025-03-02
### Added
- `summary` command now has parameter descriptions.

## [0.29.0] - 2025-03-02
### Added
- Admin slash command:
    - `toggle-average` whether to show performance averages in calculation embeds.

## [0.28.0] - 2025-03-02
### Added
- Calculate commands now have parameter descriptions.

## [0.27.0] - 2025-03-01
### Added
- Calculate commands now have parameter descriptions.

## [0.26.0] - 2025-03-01
### Added
- Admin commands now have parameter descriptions.

## [0.25.0] - 2025-03-01
### Added
- New admin slash commands:
  - Data Export:
    - `/admin-export-earnings-csv`: Export all earnings data as CSV,
    - `/admin-export-earnings-json`: Export all earnings data as JSON,
  - Role Management:
    - `/set-role`: Set a role's percentage cut,
    - `/remove-role`: Remove a role's percentage configuration,
    - `/list-roles`: List configured roles and percentages,
  - Shift Management:
    - `/set-shift`: Add a valid shift name,
    - `/remove-shift`: Remove a shift configuration,
    - `/list-shifts`: List configured shifts,
  - Period Management:
    - `/set-period`: Add a valid period name,
    - `/remove-period`: Remove a period configuration,
    - `/list-periods`: List configured periods,
  - Bonus Rules Management:
    - `/set-bonus-rule`: Set a bonus rule for a revenue range,
    - `/remove-bonus-rule`: Remove a bonus rule for a revenue range,
    - `/list-bonus-rules`: List configured bonus rules,
  - Model Management:
    - `/set-model`: Add a valid model name,
    - `/remove-model`: Remove a model configuration,
    - `/list-models`: List configured models,
  - Data Management:
    - `/clear-earnings`: Clear all earnings data (with confirmation),
    - `/reset-config`: Reset all configuration files (with confirmation),
    - `/restore-latest-backup`: Restore the latest backup (with confirmation),
- Added confirmation dialogs for destructive operations,
- Improved error handling and logging for administrative operations.

## [0.24.0] - 2025-03-01
### Added
- New admin command:
    - `admin-export-earnings-json`.

## [0.23.0] - 2025-03-01
### Added
- New admin command:
    - `admin-export-earnings-csv`.

## [0.22.0] - 2025-03-01
### Added
- Admin slash commands support.

## [0.21.0] - 2025-02-28
### Added
- Log command usage
    - Calculator commands.

## [0.20.0] - 2025-02-27
### Added
- Log command usage
    - Report commands.

## [0.19.0] - 2025-02-27
### Added
- Log command usage
    - Calculator slash commands.

## [0.18.0] - 2025-02-27
### Added
- Log command usage:
    - Admin commands.

## [0.17.0] - 2025-02-27
### Changed
- update `summary` command:
    - Rearranged fields.

## [0.16.0] - 2025-02-27
### Changed
- update `summary` command:
    - Fields are now inline.

## [0.15.0] - 2025-02-27
### Removed
- update `summary` command:
    - removed "Date Range" field.

## [0.14.3] - 2025-02-27
### Fixed
- update `summary` command period not set use-case.

## [0.14.2] - 2025-02-27
### Fixed
- update `calculate` command period, shift, role not set use-case.

## [0.14.1] - 2025-02-27
### Fixed
- update `total` command period not set use-case.

## [0.14.0] - 2025-02-27
### Changed
- `total` command update:
    - usage example updated,
    - added total gross.

## [0.13.0] - 2025-02-26
### Changed
- Rename `calculatebonuslist` to `list-bonus-rules` for better clarity.

## [0.12.0] - 2025-02-26
### Changed
- Rename `calculateperiodslist` to `list-periods` for better clarity.

## [0.11.0] - 2025-02-26
### Changed
- Rename `calculateshiftslist` to `list-shifts` for better clarity.

## [0.10.0] - 2025-02-26
### Changed
- Rename `calculateroleslist` to `list-roles` for better clarity.

## [0.9.0] - 2025-02-26
### Changed
- Rename `calculatebonus` to `set-bonus-rule` for better clarity.

## [0.8.0] - 2025-02-26
### Changed
- Rename `calculateperiodset` to `set-period` for better clarity.

## [0.7.0] - 2025-02-26
### Changed
- Rename `calculateshiftset` to `set-shift` for better clarity.

## [0.6.1] - 2025-02-26
### Changed
- Improve `CHANGELOG.md` formatting.

## [0.6.0] - 2025-02-26
### Changed
- Rename `calculateroleset` to `set-role` for better clarity.

## [0.5.0] - 2025-02-26
### Added
- Pagination to model select view.

## [0.4.1] - 2025-02-26
### Fixed
- Preview calculate-workflow ephemeral is now being properly deleted after confirmation.

## [0.4.0] - 2025-02-26
### Added
- Calculate-workflow updates:
    - Finish button is now Continue button.
    - Models are being loaded from file,
    - `Confirm & Post` / `Cancel` buttons,
    - Calculate preview before confirming it.

## [0.3.0] - 2025-02-26
### Added
- New commands:
    - `remove-bonus-rule`: Remove a bonus rule for a specific revenue range,
    - `remove-period`: Remove a selected period from configuration,
    - `remove shift`: Remove a shift configuration,
    - `remove-role`: Remove a role's percentage configuration.

## [0.2.0] - 2025-02-26
### Added
- Correct version bump:
    - instead of v0.1.9 bumped to v0.2.0.

## [0.1.9] - 2025-02-26
### Added
- Clean code and new commands:
    - `set-model`: admin command that sets new model name,
    - `remove-model`: removes a model,
    - `list-models`: gets list of all available models.

## [0.1.8] - 2025-02-25
### Added
- Finalize embedded result for calculate-workflow.

## [0.1.7] - 2025-02-25
### Added
- Model selection to the calculate-workflow.

## [0.1.6] - 2025-02-25
### Added
- Revenue input to the calculate-workflow.

## [0.1.5] - 2025-02-25
### Added
- Role selection to the calculate-workflow.

## [0.1.4] - 2025-02-25
### Added
- Shift selection to the calculate-workflow.

## [0.1.3] - 2025-02-25
### Added
- Period selection to the calculate-workflow.

## [0.1.2] - 2025-02-25
### Added
- `calculate-workflow` command that will initiate interactive workflow.

## [0.1.1] - 2025-02-25
### Added
- `cogs/calculator_slash.py` for calculator interaction workflow.

## [0.1.0] - 2025-02-25
### Added
- `main.py` system remodeled:
    - bug fixes,
    - clean code.
    - remodeled functions now being used instead.

## [0.0.22] - 2025-02-25
### Added
- Add `cogs/reports.py` for reporting functionality cogs.
- New report command:
    - summary: Generate a summary report for all earnings in a period.

## [0.0.21] - 2025-02-25
### Added
- `cogs/calculator.py` for calculator command cogs.
- New calculator commands:
    - `calculate`: Calculate earnings based on revenue, role, and shift,
    - `total`: Calculate total earnings for a period and optional date range.

## [0.0.20] - 2025-02-25
### Added
- New admin commands:
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
- `cogs/admin.py` for admin commands cogs.

## [0.0.18] - 2025-02-25
### Added
- `config/settings.py` configuration module.

## [0.0.17] - 2025-02-25
### Added
- Implemented `get_total_earnings` function in `calculations.py` for calculating total earnings from a list of earnings data.

## [0.0.16] - 2025-02-25
### Added
- Implemented `calculate_earnings` function in `calculations.py` for calculating all earnings values.

## [0.0.15] - 2025-02-25
### Added
- Implemented `find_applicable_bonus` function in `calculations.py` for finding the applicable bonus based on revenue and rules.

## [0.0.14] - 2025-02-25
### Added
- Implemented `calculate_revenue_share` function in `calculations.py` for calculating employee's cut based on gross revenue and role percentage.

## [0.0.13] - 2025-02-24
### Added
- `utils/calculations.py` for monetary calculations.

## [0.0.12] - 2025-02-24
### Added
- Implemented `validate_bonus_rules` function in `validators.py` for validation of bonus rules for consistency and overlaps.

## [0.0.11] - 2025-02-24
### Added
- Implemented `validate_period` function in `validators.py` for validation and finding a period by name (case-insensitive).

## [0.0.10] - 2025-02-24
### Added
- Implemented `validate_shift` function in `validators.py` for validation and finding a shift by name (case-insensitive).

## [0.0.9] - 2025-02-24
### Added
- Implemented `validate_date_format` function in `validators.py` for validation if a string matches the expected date format.

## [0.0.8] - 2025-02-24
### Added
- Implemented `validate_percentage` function in `validators.py` for percentage validation if value is between 0-100.

## [0.0.7] - 2025-02-24
### Added
- Implemented `parse_money` function in `validators.py` for parsing a monetary value to DecImal with proper validation.

## [0.0.6] - 2025-02-24
### Added
- `utils/validators.py` for monetary calculations.

## [0.0.5] - 2025-02-24
### Added
- Implemented `save_json` function in `file_handlers.py` for saving JSON files.

## [0.0.4] - 2025-02-24
### Added
- Implemented `load_json` function in `file_handlers.py` for reading JSON files.

## [0.0.3] - 2025-02-24
### Added
- `utils/file_handlers.py` for future file operations.

## [0.0.2] - 2025-02-24
### Added
- Logging for better debugging and monitoring.

## [0.0.1] - 2025-02-24
### Added
- `.env` for secure token management.