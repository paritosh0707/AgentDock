# Changelog - dockrion-schema

All notable changes to the `dockrion-schema` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-11-12

### Added
- Initial implementation of `dockrion-schema` package
- Pydantic models for Dockfile v1.0 specification:
  - `DockSpec` - Root specification model
  - `AgentConfig` - Agent metadata and entrypoint configuration
  - `IOSchema` and `IOSubSchema` - Input/output schema definitions
  - `ModelConfig` - LLM provider and model settings (future)
  - `Policies` - Tool and safety policies (future)
  - `AuthConfig` - Authentication and authorization settings (future)
  - `Observability` - Telemetry and monitoring configuration (future)
  - `ExposeConfig` - API exposure and network settings
  - `Metadata` - Agent metadata and tags
- Comprehensive field validators for all models:
  - Agent name format validation (lowercase, alphanumeric, hyphens)
  - Entrypoint format and injection prevention
  - Framework validation against `SUPPORTED_FRAMEWORKS`
  - Provider validation against `SUPPORTED_PROVIDERS`
  - Auth mode validation against `SUPPORTED_AUTH_MODES`
  - Log level validation against `LOG_LEVELS`
  - Streaming mode validation against `SUPPORTED_STREAMING`
  - Port range validation (1-65535)
  - Temperature range validation (0-2)
  - Rate limit format validation
  - Permissions validation
- Serialization utilities in `dockrion_schema.serialization`:
  - `to_dict()` - Convert DockSpec to dictionary
  - `from_dict()` - Create DockSpec from dictionary with validation
  - `to_yaml_string()` - Serialize DockSpec to YAML string
- JSON Schema generation in `dockrion_schema.json_schema`:
  - `generate_json_schema()` - Generate JSON Schema from DockSpec
  - `write_json_schema()` - Write JSON Schema to file
  - `get_schema_version()` - Get Dockfile schema version
- Comprehensive test suite:
  - 38 tests for model validation
  - 22 tests for serialization utilities
  - 95% code coverage
- Complete package documentation in README.md

### Dependencies
- `pydantic >= 2.0` - For data validation and serialization
- `dockrion-common` - For shared constants, validation functions, and error classes
- `pyyaml` (optional) - For YAML serialization support

### Design Principles
- **Pure Validation**: No file I/O, only validates Python dictionaries
- **Single Source of Truth**: Uses constants from `dockrion-common` package
- **Extensible**: All models use `ConfigDict(extra="allow")` for future fields
- **Security-First**: Injection prevention, port validation, value whitelisting
- **Type-Safe**: Full Pydantic v2 support with comprehensive validators

### Changed (November 12, 2024 - Post-Implementation Refinement)

#### Refactored to Use Constants from Common Package
- **Breaking Change**: Replaced hardcoded `Literal` types with `str` types validated against constants
- Changed field types to validate against `dockrion-common` constants:
  - `AgentConfig.framework`: Now `str` validated against `SUPPORTED_FRAMEWORKS`
  - `ModelConfig.provider`: Now `str` validated against `SUPPORTED_PROVIDERS`
  - `AuthConfig.mode`: Now `str` validated against `SUPPORTED_AUTH_MODES`
  - `Observability.log_level`: Now `str` validated against `LOG_LEVELS`
  - `ExposeConfig.streaming`: Now `str` validated against `SUPPORTED_STREAMING`
- All validation now happens via `@field_validator` decorators using imported constants
- Added documentation comments explaining single source of truth approach

#### Benefits of This Change
- **No Duplication**: Constants defined once in `dockrion-common`, used everywhere
- **Easy Maintenance**: Adding new frameworks/providers only requires updating `common/constants.py`
- **Consistent Validation**: All packages use the same validation rules
- **Runtime Flexibility**: Constants can be extended without recompiling schema models

### Notes
- This package is designed to be used by CLI, SDK, and Runtime Gateway
- File I/O and YAML parsing are handled by consuming packages (SDK/CLI)
- Environment variable expansion is handled by consuming packages (SDK/CLI)
- Future models (ModelConfig, Policies, AuthConfig, Observability) are defined but optional in MVP

## [Unreleased]

### Changed (November 12, 2024 - Dependency Versioning)
- **Updated dockrion-common dependency** to use proper version constraints
- Changed from `dockrion-common` (unversioned) to `dockrion-common>=0.1.1,<0.2.0`
- Ensures compatibility with common v0.1.x (ConfigDict support)
- Blocks potentially breaking v0.2.0 until schema is tested against it
- See `docs/PACKAGE_VERSIONING_STRATEGY.md` for upgrade guidelines

### Added (November 12, 2024 - I/O Schema Enhancement)

#### Comprehensive I/O Schema Validation
Enhanced `IOSubSchema` with extensive validation for edge cases:

**New Validations:**
- **JSON Schema Type Validation**: Supports all standard types (object, string, number, integer, boolean, array, null)
- **Array Type Requirements**: Arrays must define `items` schema
- **Nested Object Validation**: Properties must be valid JSON Schema objects (dicts)
- **Property Name Validation**: Cannot be empty or whitespace-only
- **Required Fields Validation**: Required fields must exist in properties
- **Duplicate Detection**: Required array cannot have duplicates
- **Complex Nested Structures**: Full support for arrays of objects, nested arrays, deeply nested objects

**New Fields:**
- Added `items` field for array type definitions
- Added `description` field for schema documentation

**16 New Tests** covering all edge cases:
- Basic and complex I/O schemas
- Nested objects and arrays
- Invalid type handling
- Property validation
- Required field validation
- Complex nested structures

**Benefits:**
- ✅ Catches malformed JSON Schema definitions early
- ✅ Prevents runtime errors from invalid I/O configurations
- ✅ Clear error messages guide users to fix issues
- ✅ Supports complex data structures (nested objects, arrays of objects)
- ✅ 98% coverage for dockfile_v1.py (up from 96%)

**Test Coverage:**
- Total tests: 76 (up from 60)
- Overall coverage: 95%
- All tests passing

### Documentation
- Created `docs/SCHEMA_EDGE_CASES_AND_VALIDATION.md` - Comprehensive edge case documentation
- Documents all validation rules, edge cases, and security considerations
- Includes examples for all supported patterns

### Planned for v0.2.0
- Activate ModelConfig validation (Phase 2)
- Activate Policies validation (Phase 2)
- Activate AuthConfig enforcement (when Auth service is ready)
- Activate Observability settings (when Telemetry is integrated)
- Add support for Dockfile v1.1+ (if needed)
- Consider full JSON Schema Draft 7 validation (if needed)

