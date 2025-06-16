# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [0.1.13] - 2025-05-06

### Fixed

- Improved Registry / File / Database toggle functionality (react)
- React App now accepts local xlsx files (react)
- Fixed missing @/lib/utils import (react)

### Added

- Ability to delete individual chat messages (streamlit)

### Changed

- Improved logging (react)

## [0.1.12] - 2025-04-30

### Changed

- Pinned streamlit to version 1.44.1 to improve stability

## [0.1.11] - 2025-04-29

### Fixed

- Fixed AI Catalog dropdown for long dataset names
- Fixed horizontal scrolling in the raw rows view
- Fixed issue with certain CSV file uploads and improved error messaging for failed uploads
- Fixed scroll area for collapsible panel with Code preview
- Fixed issue with composing message for complex character sets (Japanese/Chinese/Korean)
- Fixed issue with constantly creating new db file for each request in some cases (rest_api)

## [0.1.10] - 2025-04-17

### Fixed

- Fixed a bug where snowflake ssh keyfile was not working correctly
- Fixed the incorrect max_completion_length validation in the LLMSettings schema

### Added

- Alternative React frontend
- Allow users to use the app without an API token when it is externally shared

### Changed

- Changed the LLMSettings schema for LLM proxy settings instead of Pulumi class

## [0.1.9] - 2025-04-07

### Fixed

- Code generation inflection logic didn't quote the last but first error at retry
- Python generation prompt referred to SQL
- Fixed error when user doesn't have a last name

### Added

- Added test suite for each supported Python version

### Changed

- Installed [the datarobot-pulumi-utils library](https://github.com/datarobot-oss/datarobot-pulumi-utils) to incorporate majority of reused logic in the `infra.*` subpackages.
- Snowflake prompt more robust to lower case table and column names
- More robust code generation

## [0.1.8] - 2025-03-27

### Added

- Support for NIMs
- Support for existing TextGen deployments
- SAP Datasphere support

### Fixed

- AI Catalog and Database caching
- Fix StreamlitDuplicateElementKey error

### Changed

- Disabled session affinity for application
- Made REST API endpoints OpenAPI compliant
- Better DR token handling
- Changed AI Catalog to Data Registry

## [0.1.7] - 2025-03-07

### Added

- Shared app will use the user's API key if available to query the data catalog
- Polars added for faster big data processing
- Duck Db integration
- Datasets will be remembered as long as the session is active (the app did not restart)
- Chat sessions will be remembered as long as the session is active (the app did not restart)
- Added a button to clear the chat history
- Added a button to clear the data
- Added the ability to pick datasets used during the analysis step
- radio button to switch between snowflake mode and python mode

### Fixed

- Memory usage cut by ~50%
- Some JSON encoding errors during the analysis steps
- Snowflake bug when table name included non-uppercase characters
- pandas to polars conversion error when pandas.period is involved
- data dictionary generation was confusing the LLM on snowflake

### Changed

- More consistent logging
- use st.navigation

## [0.1.6] - 2025-02-18

### Fixed

- remove information about tools from prompt if there are none
- tools-related error fixed
- remove hard-coded environment ID from LLM deployment

## [0.1.5] - 2025-02-12

### Added

- LLM tool use support
- Checkboxes allow changing conversation
- DATABASE_CONNECTION_TYPE can be set from environment

### Fixed

- Fix issue where plotly charts reuse the same key
- Fix [Clear Data] button
- Fix logo rendering on first load
- Fix Data Dictionary editing

## [0.1.4] - 2025-02-03

### Changed

- Better cleansing report, showing more information
- Better memory usage, reducing memory footprint by up to 80%
- LLM is set to GPT 4o (4o mini can struggle with code generation)

## [0.1.3] - 2025-01-30

### Added

- Errors are displayed consistently in the app
- Invalid generated code is displayed on error

### Changed

- Additional modules provided to the code execution function
- Improved date parsing
- Default to GPT 4o mini to be compatible with the trial

## [0.1.2] - 2025-01-29

### Changed

- asyncio based frontend
- general clean-up of the interface
- pandas based analysis dataset
- additional tests
- unified renderer for analysis frontend

## [0.1.1] - 2025-01-24

### Added

- Initial functioning version of Pulumi template for data analyst
- Changelog file to keep track of changes in the project.
- pytest for api functions
