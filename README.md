# Discord Bot Implementation Plan

### Fox agency shift calculator.

### CRITICAL (Security & Core Stability)
- [x] (v0.0.1) **Secure Token Management**
    - [x] Remove hardcoded token
    - [x] Create `.env` file for token
    - [x] Add python-dotenv to requirements.txt
    - [x] Add `.env` to `.gitignore`
    - [x] Create `.env.example` template

- [ ] **File Operation Safety**
    - [x] (v0.0.3) Create utils/file_handlers for file operations
    - [x] Create JSON operation helpers
        - [x] (v0.0.4) `load_json()` with validation
        - [x] (v0.0.5) `save_json()` with atomic writes
        - [x] Implement file locking
        - [x] Add automatic backups before writes
    - [x] Add try-except blocks for all file operations
    - [x] Implement file existence checks

- [ ] **Critical Data Validation**
    - [x] (v0.0.6) Create utils/validators.py for monetary calculations
    - [ ] Monetary calculations
        - [x] (v0.0.7) Use Decimal for all calculations
        - [ ] Implement proper rounding rules (2 decimals?)
    - [ ] Input validation
        - [x] (v0.0.8) Validate percentage ranges (0-100)
        - [x] (v0.0.9) validation if a string matches the expected date format
        - [x] (v0.0.10) validation and finding a shift by name (case-insensitive)
        - [x] (v0.0.11) validation and finding a period by name (case-insensitive)
        - [ ] Check for negative values
        - [ ] Verify role existence
        - [ ] Sanitize string inputs

### HIGH PRIORITY (Core Functionality)
- [ ] **Command Safety & Validation**
    - [ ] Fix bonus calculation logic
        - [ ] Sort rules by ascending value (double check)
        - [ ] Check for overlapping ranges (double check)
        - [ ] Validate bonus amounts (double check)
    - [ ] Add permission checks
        - [ ] Verify admin status
        - [ ] Check command permissions
    - [ ] Implement proper error messages

- [ ] **Date & Time Handling**
    - [ ] Add time zone support (Is it really necessary?)
    - [ ] Fix date range calculations
    - [ ] Validate date formats
    - [ ] Standardize date display

- [ ] **Basic Logging**
    - [ ] Set up logging configuration
    - [ ] Log command usage
    - [ ] Log calculation results
    - [ ] Log errors with stack traces
    - [ ] Implement log rotation

### MEDIUM PRIORITY (Structure)
- [ ] **Code Organization**
    - [ ] Split into modules
        - [ ] `commands.py` (command logic)
        - [ ] `utils.py` (helpers)
        - [ ] `config.py` (configuration)
        - [ ] `calculations.py` (business logic)
    - [ ] Create `main.py` as entry point
    - [ ] Convert to Discord.py Cogs

- [ ] **Configuration Management**
    - [ ] Add config reload function
    - [ ] Create config validation
    - [ ] Optimize lookups
        - [ ] Use dictionaries instead of lists
        - [ ] Case-insensitive matching

### USER EXPERIENCE
- [ ] **Command Improvements**
    - [ ] Add management commands
        - [ ] `!calculateroleremove`
        - [ ] `!calculateshiftremove`
        - [ ] `!calculateperiodremove`
        - [ ] `!calculateroleslist`
        - [ ] `!calculateshiftslist`
    - [ ] Add help messages
        - [ ] Usage examples
        - [ ] Parameter descriptions

- [ ] **Display Enhancements**
    - [ ] Improve embeds
        - [ ] Add thousand separators
        - [ ] Consistent formatting
        - [ ] Color coding
    - [ ] Add confirmation reactions
    - [ ] Implement command cooldowns

### FUTURE IMPROVEMENTS
- [ ] Basic report generation
- [ ] CSV/JSON data export
- [ ] Bulk calculations
- [ ] Simple statistics commands
- [ ] Documentation
    - [ ] README.md
    - [ ] Setup guide
    - [ ] Command reference

---

### Excluded Features:
- Database integration (staying with JSON) (at the very end.. maybe even skip it)
- Web dashboard (will see If needed like admin dashboard)
- Charts/visualizations