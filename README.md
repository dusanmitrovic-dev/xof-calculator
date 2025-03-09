### Fox agency shift calculator.

# Discord Bot Implementation Plan

## CRITICAL (Security & Core Stability)

### Secure Token Management

- [x] (v0.0.1) **Secure Token Management**
    - [x] Remove hardcoded token
    - [x] Create `.env` file for token
    - [x] Add python-dotenv to requirements.txt
    - [x] Add `.env` to `.gitignore`
    - [x] Create `.env.example` template

### File Operation Safety

- [x] (v0.0.3) Create `utils/file_handlers` for file operations
- [x] Create JSON operation helpers
    - [x] (v0.0.4) `load_json()` with validation
    - [x] (v0.0.5) `save_json()` with atomic writes
    - [x] Implement file locking
    - [x] Add automatic backups before writes
- [ ] Add automatic cloud backups before writes
- [x] Add try-except blocks for all file operations
- [x] Implement file existence checks

### Critical Data Validation

- [x] (v0.0.6) Create `utils/validators.py` for monetary calculations
- [x] Monetary calculations
    - [x] (v0.0.7) Use Decimal for all calculations
    - [x] Implement proper rounding rules (2 decimals?)
- [x] Input validation
    - [x] (v0.0.8) Validate percentage ranges (0-100)
    - [x] (v0.0.9) Validate if a string matches the expected date format
    - [x] (v0.0.10) Validate and find a shift by name (case-insensitive)
    - [x] (v0.0.11) Validate and find a period by name (case-insensitive)
    - [x] (v0.0.12) Validate bonus rules for consistency and overlaps
    - [x] Check for negative values
    - [x] Sanitize string inputs

## HIGH PRIORITY (Core Functionality)

### Core Calculation Functions

- [x] (v0.0.13) Create `utils/calculations.py` for monetary calculations
- [x] (v0.0.14) Calculate employee's cut based on gross revenue and role percentage
- [x] (v0.0.15) Find the applicable bonus based on revenue and rules
- [x] (v0.0.16) Calculate all earnings values
- [x] (v0.0.17) Calculate total earnings from a list of earnings data
- [x] (v0.0.18) Create `config/settings.py` configuration module

### Admin Commands

- [x] (v0.0.19) Create `cogs/admin.py` for admin commands
- [x] (v0.0.20) New admin commands:
    - [x] `calculateroleset`: set a role's percentage cut
        - [x] (v0.6.0) Change to `setrole` or `set-role`
    - [x] `calculateshiftset`: add a valid shift name
        - [x] (v0.7.0)  Change to `setshift` or `set-shift`
    - [x] `calculateperiodset`: add a valid period name
        - [x] (v0.8.0) Change to `setperiod` or `set-period`
    - [x] `calculatebonus`: set a bonus rule for a revenue range
        - [x] (v0.9.0) Change to `setbonus` or `set-bonus-rule`
    - [x] `calculateroleslist`: list all configured roles and their percentages
        - [x] (v0.10.0) Change to `listroles` or `list-roles`
    - [x] `calculateshiftslist`: list all configured shifts
        - [x] (v0.11.0) Change to `listshifts` or `list-shifts`
    - [x] `calculateperiodslist`: list all configured periods
        - [x] (v0.12.0) Change to `listperiods` or `list-periods`
    - [x] `calculatebonuslist`: list all configured bonus rules
        - [x] (v0.13.0)  Change to `listbonus` or `list-bonus-rules`
    - [x] (v0.2.0) `set-model`: add a new model (`set-model peanut`)
    - [x] (v0.2.0) `list-models`: list all available models
    - [x] (v0.29.0) `toggle-average` whether to show performance averages in calculation embeds

### Calculator Commands

- [x] (v0.1.1) Create `cogs/calculator_slash.py` for calculator interaction workflow
    - [x] (v0.1.2) Add `calculate-workflow` command that will initiate interactive workflow
        - [x] Find more appropriate name (`/calculate workflow`)
        - [x] (v0.1.3) Add period selection to the workflow
        - [x] (v0.1.4) Add shift selection to the workflow
        - [x] (v0.1.5) Add role selection to the workflow
        - [x] (v0.1.6) Add revenue input to the workflow
        - [x] (v0.1.7) Add model selection to the workflow
        - [x] (v0.1.8) Finalize embedded result for calculate-workflow
        - [x] (v0.4.0) Finish button renamed to Continue
        - [x] (v0.4.0) Load models from the `models_config.json`
        - [x] (v0.4.0) Confirm & Post/Cancel buttons for calculate workflow command
        - [x] (v0.4.0) Calculate preview before confirming it
        - [x] (v0.4.1) Fix preview ephemeral not being deleted
        - [x] (v0.5.0) Add pagination to model select view
            - [ ] Do any other use-cases need pagination?
- [x] (v0.22.0) Add admin slash commands support
    - [x] (v0.23.0) `admin-export-earnings-csv` command
    - [x] (v0.24.0) `admin-export-earnings-json` command
    - [x] (v0.25.0) `/admin-export-earnings-csv`: Export all earnings data as CSV
    - [x] (v0.25.0) `/admin-export-earnings-json`: Export all earnings data as JSON
    - [x] (v0.25.0) `/set-role`: Set a role's percentage cut
    - [x] (v0.25.0) `/remove-role`: Remove a role's percentage configuration
    - [x] (v0.25.0) `/list-roles`: List configured roles and percentages
    - [x] (v0.25.0) `/set-shift`: Add a valid shift name
    - [x] (v0.25.0) `/remove-shift`: Remove a shift configuration
    - [x] (v0.25.0) `/list-shifts`: List configured shifts
    - [x] (v0.25.0) `/set-period`: Add a valid period name
    - [x] (v0.25.0) `/remove-period`: Remove a period configuration
    - [x] (v0.25.0) `/list-periods`: List configured periods
    - [x] (v0.25.0) `/set-bonus-rule`: Set a bonus rule for a revenue range
    - [x] (v0.25.0) `/remove-bonus-rule`: Remove a bonus rule for a revenue range
    - [x] (v0.25.0) `/list-bonus-rules`: List configured bonus rules
    - [x] (v0.25.0) `/set-model`: Add a valid model name
    - [x] (v0.25.0) `/remove-model`: Remove a model configuration
    - [x] (v0.25.0) `/list-models`: List configured models
    - [x] (v0.25.0) `/clear-earnings`: Clear all earnings data (with confirmation)
    - [x] (v0.25.0) `/reset-config`: Reset all configuration files (with confirmation)
    - [x] (v0.25.0) `/restore-latest-backup`: Restore the latest backup (with confirmation)
- [x] (v0.0.21) Create `cogs/calculator.py` for calculator commands
- [x] New calculator commands:
    - `calculate`: Calculate earnings based on revenue, role, and shift
        - [x] Store role in earnings as well (detailed logs for that specific shift with role tracking)
    - `total`: Calculate total earnings for a period and optional date range
        - [x] (v0.14.0) Add total gross calculation

### Reporting Functionality

- [x] (v0.0.22) Add `cogs/reports.py` for reporting functionality
- [x] New report command:
    - `summary`: Generate a summary report for all earnings in a period
        - [x] (v0.30.0) add parameter description

### Command Safety & Validation

- [x] Fix bonus calculation logic
    - [x] Sort rules by ascending value (double check)
    - [x] Check for overlapping ranges (double check)
    - [x] Validate bonus amounts (double check)
- [x]  Add permission checks
    - [x] Verify admin status
    - [x] Check command permissions
- [x] Implement proper error messages

### Date & Time Handling

- [x] Fix date range calculations
- [x] Validate date formats
- [x] Standardize date display

### Basic Logging

- [x] Set up logging configuration
- [x] Log command usage
    - [x] (v0.18.0) Admin commands
    - [x] (v0.20.0) Report commands
    - [x] (v0.21.0) Calculation commands and results
    - [x] (v0.19.0) Calculate slash commands and results
- [x] Log errors with stack traces
- [x] Implement log rotation (5MB)

## MEDIUM PRIORITY (Structure)

### Code Organization

- [x] Split into modules
    - [x] `admin.py` (admin command logic cogs)
    - [x] `calculator.py` (calculator logic cogs)
    - [x] `reports.py` (reports logic cogs)
    - [x] `file_helpers.py` (helpers)
    - [x] `validators.py` (helpers)
    - [x] `settings.py` (configuration)
    - [x] `calculations.py` (business logic)
- [x] Create `main.py` as entry point
- [x] Convert to Discord.py Cogs

## USER EXPERIENCE

### Command Improvements

- [x] New well-thought command names
- [x] Add management commands
    - [x] (v0.2.0) `remove-model`
    - [x] (v0.3.0) `remove-role`
    - [x] (v0.3.0) `remove-shift`
    - [x] (v0.3.0) `remove-period`
    - [x] (v0.3.0) `remove-bonus-rule`
- [ ] Add help messages
    - [x] Usage examples
    - [ ] Parameter descriptions
        - [x] (v0.26.0) Admin commands
        - [ ] Calculate commands
            - [ ] Even tho set not displaying it for `calculate`
            - [x] (v0.27.0) `total` parameters set
    - [ ] Add detailed help messages for all commands (double check)
- [ ] All admin slash commands are to be ephemeral

### Display Enhancements

- [ ] Improve embeds
    - Different ways of representing calculate responses?
- [x] Add confirmation reactions

### Pre v1.0.0 release fixes and improvements
- [x] (v0.32.1) removed slash `set-model` command duplicate method
- [ ] Each backup will have separate restore command
- [x] (❌) (v0.34.0) `toggle-average` better error handling
- [x] (v0.35.0) `admin-export-earnings-csv` command renamed to `export-earnings-csv` for simplicity
- [x] (v0.36.0) `export-earnings-csv` command usage updated to follow new command name
- [x] (v0.37.0) `admin-export-earnings-json` command renamed to `export-earnings-json` for simplicity
- [x] (v0.38.0) `export-earnings-json` command usage updated to follow new command name
- [x] (❌) (v0.39.0) `set-role` better error handling
- [x] (❌) (v0.40.0) `remove-role` better error handling
- [x] (❌) (v0.41.0) `set-shift` better error handling
- [x] (❌) (v0.42.0) `remove-shift` better error handling
- [x] (❌) (v0.43.0) `set-period` better error handling
- [x] (v0.45.0) Reset Slash Individual Config Files:
    - [x] (v0.45.0) `reset-shift-config`
    - [x] (v0.45.0) `reset-period-config`
    - [x] (v0.45.0) `reset-role-config`
    - [x] (v0.45.0) `reset-bonus-config`
    - [x] (v0.45.0) `reset-earnings-config`
    - [x] (v0.73.0) `reset-display-config`
- [x] (v0.45.0) Restore Slash Individual Backup Files:
    - [x] (v0.45.0) `restore-shift-backup`
    - [x] (v0.45.0) `restore-period-backup`
    - [x] (v0.45.0) `restore-role-backup`
    - [x] (v0.45.0) `restore-bonus-backup`
    - [x] (v0.45.0) `restore-earnings-backup`
    - [x] (v0.73.0) `restore-display-config`
- [x] (v0.55.0) `help` list slash commands for admins and normal users
- [x] (v0.55.0) `view-earnings` view your earnings or earnings of a specified user
- [x] (v0.56.0) `view-earnings` admin able to see for specific user, user only theirs
    - [x] (v0.56.0) `view-earnings-admin` admin will see users earning entries
    - [x] (v0.56.0) `view-earnings` user command version
- [x] (v0.72.0) Admin slash toggle that shows ephemeral messages to everyone or hides
    - `toggle-ephemeral`
- [x] (v0.73.0) `reset-config` needs to reset display settings
- [x] (v0.74.0) `reset-config` uses helper reset functions
- [ ] Fully ephemeral slash commands
    - [x] (v0.75.0) `set-role`
    - [x] (v0.72.0) `set-period`
    - [x] (v0.76.0) `remove-role`
    - [x] (v0.76.0) `list-roles`
    - [x] (v0.90.0) `set-shift`
    - [x] (v0.91.0) `remove-shift`
    - [x] (v0.92.0) `remove-period`
    - [x] (v0.93.0) `list-shifts`
    - [x] (v0.94.0) `list-periods`
    - [x] (v0.95.0) `list-bonus-rules`
    - [x] (v0.96.0) `set-bonus-rule`
    - [x] (v0.97.0) `list-models`
    - [x] (v0.98.0) `set-model`
    - [x] (v0.99.0) `remove-model`
    - [x] (v0.100.0) `toggle-average`
    - [x] make helper functions
- [ ] Remove `reset-earnings-config`
- [ ] Separate data and backup data
- [x] (v0.77.0) Remove hours for commission views
- [x] (v0.77.0) Remove net revenue in hourly views
- [x] (v0.78.0) Better preview and finalize display
- [x] (v0.79.0) Export options for `view-earnings` and `view-earnings-admin`
    - [x] (v0.79.0) CSV
    - [x] (v0.79.0) TXT
    - [x] (v0.80.0) JSON
    - [x] (v0.80.0) Excel
    - [x] (v0.80.0) PDF
    - [x] (v0.80.0) PNG Chart
    - [x] (v0.80.0) ZIP Archive
- [x] (v0.80.1) Fix bug where view-earnings command did not display
- [x] (v0.80.2) Fix export zip functionality
- [x] (v0.81.0) New command view-earnings-table
- [x] (v0.81.0) `range_from` and `range_to` parameters
- [x] (v0.81.0) `send_to` functionality
- [x] (v0.82.0) `view-earnings-admin-table`
- [x] (v0.83.0) Improve earnings display with separators and additional fields
- [x] (v0.83.0) Implement error handling for export failures
- [x] Update other `view-earnings` methods
    - [x] (v0.84.0) `view-earnings-admin-table`
    - [x] (v0.85.0) `view-earnings-admin`
    - [x] (v0.86.0) `view-earnings-table`
- [x] (v0.87.0) Merge `view-earnings` functions and add new `as_table` parameter
- [ ] Add functionality to select column names to display in `view-earnings`
- [ ] Pip freeze > requirements.txt
- [ ] View earnings remove period use role instead
- [ ] New view earnings slash command `view-earnings date-from date-to weekly/monthly`
- [x] View earnings export
- [ ] Bulk earnings for everyone from period to period for weekly/monthly
    - [ ] With DM support notification that sends to everyone their earnings log
- [ ] Any way to use a date picker for `view-earnings`?
    - https://discord-date-2.shyked.fr/
- [ ] Bot roles
- [ ] ONE ADMIN COMMAND TO RULE THEM ALL ! (LOL)

# Commission Settings Implementation TODO

## Configuration Commands
- [x] (v0.57.0) Implement `/set-role-commission` command
- [x] (v0.57.0) Implement `/set-role-hourly` command
- [x] (v0.57.0) Implement `/set-user-commission` command
- [x] (v0.57.0) Implement `/set-user-hourly` command
- [x] (v0.57.0) Implement `/view-commission-settings` command
- [x] (v0.65.0) Implement `toggle-user-role-override` command
- [x] (v0.66.0) Make them admin slash ephemeral
- [x] (v0.63.0) Update configuration commands for new `commission_settings.json` structure
- [x] (v0.63.0) Compensation view gets edited instead of staying untouched.
- [x] (v0.64.0) Commission commands to be admin only
- [x] (v0.68.0) `reset-config` update to reset compensation settings as well
- [x] (v0.69.0) New command `clear-compensation`
- [x] (v0.70.0) `clear-compensation` renamed to `reset-compensation-config`
- [x] (v0.71.0) New command `restore-compensation-backup` 

## Data Management
- [x] (v0.57.0) Create `commission_settings.json` in `data/` directory
- [x] (v0.57.0) Add input validation for commission percentages
- [x] (v0.57.0) Add input validation for hourly rates
- [x] (v0.57.0) Create backup mechanism for settings file
- [x] (v0.58.0) Add compensation step to the workflow
- [x] Add guild id entry that wraps data
- [x] Do hourly only get bonus for gross?
    - YES
- [x] (v0.67.0) Remove loggers from preview method
- [x] Block cases that do not have set % or $/h from attempting
    - or handle properly
- [x] (v0.64.0) fix role logic for commission settings
 
## Calculation Logic Integration
- [x] (v0.59.0) `calculate_hourly_earnings` method
- [x] Calculate priority
    - [x] (HIGHEST) User commission and hourly
    - [x] (MEDIUM) Role commission and hourly
- [x] Modify existing earnings calculation to use commission settings 
- [x] Implement rate selection logic:
  - User-specific rates with override
  - Role-based fallback
- [x] (v0.66.0) Calculate workflow will only show roles that user has

## FUTURE IMPROVEMENTS

- [ ] Better image display in `calculate` command
    - Like button that opens up `stash` with attachments
- [x] (v0.23.0) CSV data export
- [x] (v0.24.0) JSON data export
- [ ] Documentation
    - [ ] `README.md`
    - [ ] Setup guide
    - [ ] Command reference

---

### Excluded Features:

- Database integration (staying with JSON) (at the very end... maybe even skip it)
- Web admin dashboard (will see if needed like admin dashboard)
    - Adding and removing roles, shifts etc. over web page

