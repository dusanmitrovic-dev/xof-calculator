# Changelog

## [Unreleased]

## [1.0.3] - 2025-06-11
- Stable release with bot landing page.

## [1.0.2] - 2025-04-3
### Fixed
- Update version display.

## [1.0.1] - 2025-04-3
### Fixed
- Fix commission and hourly rate handling with overrides and added missing `/restore-shift-config`.

## [1.0.0] - 2025-03-27
### Added
- First major release.

## [0.171.0] - 2025-03-25
### Added
- Enabled self server backups.

## [0.170.0] - 2025-03-25
### Changed
- Enhance `/manage-backups` command with backup type selection and improved error handling and `/copy-earnings-from-the-server`.

## [0.169.0] - 2025-03-25
### Changed
- Enhance `/copy-config-from-the-server` command.

## [0.168.0] - 2025-03-25
### Changed
- Enhance `/view-config` command.

## [0.167.0] - 2025-03-25
### Fixed
- Fixed `/reset-config` command to properly reset models data.

## [0.166.0] - 2025-03-25
### Change
- Enhanced `/copy-earnings-from-the-server` command.

## [0.165.0] - 2025-03-24
### Change
- Update `!` commands to use guild-specific paths.

## [0.164.0] - 2025-03-24
### Change
- Update `!summary` earnings and period data file retrieval to use guild-specific paths.

## [0.163.1] - 2025-03-24
### Remove
- Remove `data/earnings` test residual files.

## [0.163.0] - 2025-03-24
### Changed
- Updated earnings slash calculate commands to use multiple servers file logic.

## [0.162.0] - 2025-03-23
### Changed
- Update display settings, help command and reset restore full config for guild-specific configurations.

## [0.161.0] - 2025-03-23
### Changed
- Update compensation settings for guild-specific configurations.

## [0.160.0] - 2025-03-23
### Changed
- Update bonus settings for guild-specific configurations.

## [0.159.0] - 2025-03-23
### Changed
- Update period settings for guild-specific configurations.

## [0.158.0] - 2025-03-23
### Changed
- Update shift settings for guild-specific configurations.

## [0.157.0] - 2025-03-23
### Changed
- Update role settings for guild-specific configurations.

## [0.156.0] - 2025-03-22
### Changed
- Update models and display settings for guild-specific configurations.

## [0.155.0] - 2025-03-22
### Rollback
- To `v0.154.1` due to bad multiple server file logic.

## [0.154.2] - 2025-03-22
### Changed
- First attempt to for multiple server file organization. Requires rollback to `v0.154.1`.

## [0.154.1] - 2025-03-22
### Changed
- Modified `CHANGELOG.md` for better formatting.

## [0.154.0] - 2025-03-21
### Refactored
- Converted buffer generation methods to async for improved performance,
- Enhanced display settings management and improved admin command handling,
- Clarified admin permissions in report sending and updated help command descriptions,
- Updated earnings summary title to reflect user context and cleaned up commented code,
- Simplified report title and updated footer formatting for consistency,
- Formatted total cut as currency and updated footer styling for sale ID,
- Improved legend positioning and styling for better chart clarity,
- Enhanced table readability with improved font size, padding, and vertical alignment.

## [0.153.0] - 2025-03-20
### Changed
- Enhance table formatting and improve chart layout for better readability.

## [0.152.0] - 2025-03-20
### Removed
- remove unused `SVG` export functionality.

## [0.151.0] - 2025-03-20
### Changed
- Update remove sale command to handle multiple sale IDs and improve user feedback.

## [0.150.0] - 2025-03-20
### Changed
- Enhance removal confirmation message to include user details and streamline entry count logic.

## [0.149.0] - 2025-03-20
### Changed
- Add command to remove earnings entry by ID and User with confirmation.

## [0.148.0] - 2025-03-20
### Changed
- Update earnings file handling to use guild-specific paths.

## [0.147.0] - 2025-03-20
### Changed
- Include Sale ID in entry display for improved tracking.

## [0.146.0] - 2025-03-20
### Changed
- Update earnings data handling to use guild-specific files.

## [0.145.0] - 2025-03-20
### Changed
- Replace unique ID generation with a new method using timestamp and random digits.

## [0.144.0] - 2025-03-20
### Changed
- Updated currency formatting to use settings for decimal places,
- Added unique IDs to entries in `calculator_slash`,
- Improved formatting for hours worked, hourly rate, commission, and revenue calculations,
- Standardized thousands separator usage in all currency-related outputs,
- Ensured consistent percentage and hourly rate formatting (`/h` suffix, `%` for commission),
- Refactored compensation formatting for better readability.

## [0.143.0] - 2025-03-18
### Fixed
- Simplify revenue calculations by removing quantization. 

## [0.142.0] - 2025-03-18
### Fixed
- Decimal handling in bonus rule parsing, avoid unnecessary conversions.

## [0.141.0] - 2025-03-18
### Fixed
- Include `all_data` parameter in format buffer generation for zip export.

## [0.140.0] - 2025-03-18
### Fixed
- Ensure hourly rate defaults to "0" for better handling of missing values.

## [0.139.0] - 2025-03-18
### Fixed
- Improve commission percentage handling and update README for clarity.

## [0.138.0] - 2025-03-18
### Added
- Added error handling for invalid date format in earnings command,
- Included member username in revenue comparison chart for better identification,
- Included member username in display name for clarity,
- Corrected title in user revenue comparison chart to improve clarity.

## [0.137.0] - 2025-03-17  
### Changed  
- Simplify user revenue comparison chart by removing dynamic legend configuration and adjusting layout.

## [0.136.0] - 2025-03-17  
### Changed  
- Update PDF generation to include interaction handling and improve report titles.

## [0.135.0] - 2025-03-17  
### Changed  
- Enhance earnings visualization by aggregating data and updating labels.

## [0.134.0] - 2025-03-17  
### Removed  
- Remove unused report admin commands from help embed.

## [0.133.0] - 2025-03-17  
### Removed  
- Cleaned up commented-out code in multiple files (`admin_slash`, `calculator_slash`, `help_slash`).  

### Changed  
- Improved error handling for PDF generation and plot creation in `calculator_slash`,
- Enhanced data validation and date formatting in earnings-related plots.  

## [0.132.0] - 2025-03-14  
### Added  
- Support for `all_data` in Markdown export,
- Support for `all_data` in PDF export,
- Support for `all_data` in Excel export,  
- Updated export methods to handle `all_data` properly,
- List now displays `username` and `user display name`,
- First, second, and final attempts at `unlimited embed length` for tables and lists.  

### Changed  
- `PDF display` was updated,
- `HTML display` was modified,  
- `Generated file names` now reflect `all_data` set.  

### Fixed  
- Tables `no longer include '$' signs`,
- Table display issues were resolved,
- Fixed `TXT and CSV display issues`,
- Fixed error in `_generate_txt()` function (`positional argument mismatch`).  

### Removed  
- `Residual commented-out` `generate_export_file` method.

## [0.131.0] - 2025-03-12
### Added
- Selection by `period` command parameter.

## [0.130.0] - 2025-03-12
### Changed
- Upgraded `create_list_embed` method.

## [0.129.0] - 2025-03-12
### Removed
- Final version for `svg` export.

## [0.128.0] - 2025-03-12
### Removed
- Final version for `png` export.

## [0.128.0] - 2025-03-12
### Removed
- Removed charts from excel generation since they did not work.

## [0.127.0] - 2025-03-12
### Removed
- Removed charts from excel generation since they did not work.

## [0.126.0] - 2025-03-12
### Removed
- Removed `hourly_rate` and `commission_percent` from export.

## [0.125.0] - 2025-03-12
### Added
- Display warning if `zip_formats` are set but `export` is not `zip`.

## [0.124.0] - 2025-03-12
### Added
- Added zip formats selection.

## [0.123.0] - 2025-03-11
### Changed
- New export types and updated existing ones.

## [0.122.0] - 2025-03-11
### Changed
- Now displaying successfully sent to user list.

## [0.121.0] - 2025-03-11
### Changed
- Direct mentions now include username.

## [0.120.0] - 2025-03-11
### Changed
- Changed footer for earnings report delivery summary.

## [0.119.0] - 2025-03-11
### Fixed
- Successfully sending files to each send_to included user.

## [0.118.0] - 2025-03-11
### Fixed
- Correctly displaying report message sent.

## [0.117.0] - 2025-03-11
### Added
- Functional success count to `view-earnings` `send_to` statistic.

## [0.116.0] - 2025-03-11
### Changed
- DM-ed users first receive table then file.

## [0.115.0] - 2025-03-11
### Added
- `send_to` argument of `view-earnings` command now sends to multiple users and roles.

## [0.114.0] - 2025-03-10
### Rollback
- Reverting project to `v0.113.0` state.

## [0.113.0] - 2025-03-10
### Removed
- Removed deprecated methods:
    - `view-earnings-table`,
    - `view-earnings-table-admin`,
    - `view-earnings-admin`.

## [0.112.0] - 2025-03-10
### Added
- `view-earnings` command will now tag user to whom it sent DM.

## [0.111.0] - 2025-03-10
### Added
- Add sent by field in report message sent to the `sent_to` user in `view-earnings` command.

## [0.110.0] - 2025-03-10
### Changed
- `view-earnings` now has `user` admin parameter that allows to select user which earnings will be displayed.

## [0.109.0] - 2025-03-10
### Changed
- Second stage of merging `view-earnings` and `view-earnings-table`,
- View earnings is now working independently,
- `send_to_message` command parameter added.

## [0.107.0] - 2025-03-10
### Changed
- First stage of merging `view-earnings` and `view-earnings-table`.

## [0.106.0] - 2025-03-09
### Changed
- Command `calculate workflow` now fully supports ephemeral logic.

## [0.105.0] - 2025-03-09
### Fixed
- Fixed backup restoration process with improved interaction handling.

## [0.104.0] - 2025-03-09
### Changed
- commands that now have full ephemeral support:
    - `view-compensation-settings`,
    - `set-role-commission`,
    - `set-role-hourly`,
    - `set-user-commission`,
    - `set-user-hourly`,
    - `toggle-user-role-override`,
    - `help` slash.

## [0.103.0] - 2025-03-09
### Changed
- commands that now have full ephemeral support:
    - `clear-earnings`,
    - `view-display-settings`,
    - `list-models`,
    - `reset-config`,
    - `restore-latest-backup`,
    - `reset-role-config`,
    - `reset-bonus-config`,
    - `reset-models-config`,
    - `reset-compensation-config`,
    - `reset-display-config`,
    - `restore-role-backup`,
    - `restore-bonus-backup`,
    - `restore-earnings-backup`,
    - `restore-models-backup`,
    - `restore-compensation-backup`,
    - `restore-display-backup`,
- removed `[Admin]` from command descriptions,
- removed `reset-earnings-config` command,
- `clear-earnings` now has a "Confirm" and "Cancel" buttons,
- removed unnecessary command descriptions,
- renamed `reset_models_settings` to `reset_models`,
- new command `view-display-settings`.

## [0.102.0] - 2025-03-09
### Changed
- `reset-period-config` now has fully ephemeral support,
- `restore-period-backup` now has fully ephemeral support.

## [0.101.0] - 2025-03-09
### Changed
- `reset-shift-config` now has fully ephemeral support,
- `restore-shift-backup` now has fully ephemeral support,
- `save_json` has a new argument `make_backup` which allows you to save a backup if set to `True` (default is `True`).

## [0.100.0] - 2025-03-09
### Changed
- `toggle-average` now has fully ephemeral support.

## [0.99.0] - 2025-03-09
### Changed
- `remove-model` now has fully ephemeral support.

## [0.98.0] - 2025-03-09
### Changed
- `set-model` now has fully ephemeral support.

## [0.97.0] - 2025-03-09
### Changed
- `list-models` now has fully ephemeral support.

## [0.96.0] - 2025-03-09
### Changed
- `set-bonus-rule` now has fully ephemeral support.

## [0.95.0] - 2025-03-09
### Changed
- `list-bonus-rules` now has fully ephemeral support.

## [0.94.0] - 2025-03-09
### Changed
- `list-periods` now has fully ephemeral support.

### Removed
- Removed `bonus-rules.json` extra file from project root.

## [0.93.0] - 2025-03-09
### Changed
- `list-shifts` now has fully ephemeral support.

## [0.92.0] - 2025-03-09
### Changed
- `remove-period` now has fully ephemeral support.

## [0.91.0] - 2025-03-09
### Changed
- `remove-shift` now has fully ephemeral support.

## [0.90.0] - 2025-03-08
### Changed
- `set-shift` now has fully ephemeral support.

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
- Add send_to, range_from, and range_to parameters.
- Implement date filtering and recipient management.

## [0.84.0] - 2025-03-08
### Changed
- feat(calculator_slash): enhance `view-earnings-admin-table` command with improved descriptions and recipient handling.

## [0.83.0] - 2025-03-08
### Added
- Added `range_from` and `range_to` parameters for filtering earnings by date,
- Implemented `send_to` functionality to send reports via DM to users/roles,
- Improved earnings display with separators and additional fields,
- Enhanced export handling with better error messages.

## [0.82.0] - 2025-03-08
### Added
- Updated new functionalities for `view-earnings-admin-table` command.

## [0.81.0] - 2025-03-08
### Added
- `range_from` and `range_to` parameters,
- send_to: that will send report to the user DM,
- new export formats for `view-earnings-table`,
- new command `view-earnings-table`.

## [0.80.2] - 2025-03-08
### Fixed
- Fixed export zip functionality with better base naming.

## [0.80.1] - 2025-03-07
### Fixed
- Fix bug where view-earnings command did not display:

Resolved issue where both `view-earnings` and `view-earnings-table` had the same method name
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
- `reset-config` now uses helper reset functions.

## [0.73.0] - 2025-03-07
### Added
- `reset-display-config`,
- `restore-display-config`,
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
    - clean code,
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