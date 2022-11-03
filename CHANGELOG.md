# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2022-11-03
### Added
- Support setting up OpenVPN credentials (username and password)

### Changed
- Remove Python 2 style syntax from tests

## [0.6.0] - 2022-01-26
### Changed
- Do not activate VPN client right after adding config

## [0.5.1] - 2020-12-04
### Changed
- Migrate CHANGELOG to [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) style

### Fixed
- Force firewall reload after adding new vpn client

## [0.5] - 2020-11-10
### Changed
- linter fixes and cleanup of deprecated code

### Fixed
- sanitize input characters in client config file name
- limit interface name length

## [0.4] - 2020-10-06
### Added
- Automatically add VPN into new firewall zone

## [0.3] - 2020-07-03
### Fixed
- sanitize id while adding client

### Removed
- remove unnecessary announcer

## [0.2] - 2019-10-09
### Added
- add 'running' indicator to client list

## [0.1] - 2019-08-22
### Added
- initial functionality implemented
