# CHANGELOG Guidelines

## Naming Convention
- The file should always be named `CHANGELOG.md`
- Use all uppercase letters for the filename to make it easily noticeable in project directories

## Format and Structure

### Header
Start your changelog with:
```
# Changelog
All notable changes to this project will be documented in this file.

This format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
```

### Version Sections
- List versions in reverse chronological order (newest on top)
- Always keep an `[Unreleased]` section at the top for upcoming changes
- Format version headers as follows:
  ```
  ## [X.Y.Z] - YYYY-MM-DD
  ```
  where X.Y.Z follows semantic versioning:
  - X: Major version (breaking changes)
  - Y: Minor version (new features, backwards compatible)
  - Z: Patch version (backwards compatible bug fixes)

### Change Types
Group changes under the following categories:
- **Added** - for new features
- **Changed** - for changes in existing functionality
- **Deprecated** - for soon-to-be removed features
- **Removed** - for now removed features
- **Fixed** - for any bug fixes
- **Security** - in case of vulnerabilities
- **Rollback** - when reverting to a previous version

### Example Entry
```
## [1.0.0] - 2024-10-03
### Added
- New user authentication system
### Changed
- Upgraded database to PostgreSQL 13
### Fixed
- Resolved issue with cache invalidation
```

## Best Practices

1. **Keep it Simple**: Write clear, concise entries that future you (and others) will understand
2. **Be Consistent**: Use consistent formatting and language throughout
3. **Link Versions**: Add reference links at the bottom of the file:
   ```
   [Unreleased]: https://github.com/username/repo/compare/v1.0.0...HEAD
   [1.0.0]: https://github.com/username/repo/compare/v0.1.0...v1.0.0
   ```
4. **Include Practical Details**: 
   - Mention ticket/issue numbers when relevant
   - Include migration instructions for breaking changes
5. **Keep it Human-Readable**: Write for humans, not machines

## Example CHANGELOG.md

```
# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.1.0] - 2024-10-04
### Added
- Export functionality for reports (#123)
### Changed
- Improved loading speed of dashboard

## [1.0.0] - 2024-10-03
### Added
- Initial release of core features
- User authentication system
### Changed
- Upgraded database to PostgreSQL 13

[Unreleased]: https://github.com/username/repo/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/username/repo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/username/repo/releases/tag/v1.0.0
```