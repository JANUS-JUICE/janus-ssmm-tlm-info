# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 0.0.9 - 2026-07-22

### Added

- `group_files_by_shared_images()`: groups SSMM files whose packets share at least one image (SESSION_ID, IMG_COUNT), for detecting when an image is split across multiple physical files
- `--quick` CLI/`quick=` `ssm_file_info()` option: parses only each file's first and last packet instead of every packet, for a much faster approximate summary on large files
- `--raw` CLI option: outputs JSON instead of a formatted table
- `--summary`/`--gap-hours` CLI options and `summarize_infos_by_time_gap()`: group files into contiguous blocks of telemetry separated by gaps larger than a configurable threshold (default 24h)
- CLI output is now rendered as a `rich` table instead of plain text

### Fixed

- `ssm_file_info()` no longer crashes with a cryptic `TypeError` on empty or packet-less SSMM files; it now raises a clear `ValueError`
- The CLI no longer aborts an entire batch when one file fails to parse; it logs the error and continues with the rest
- CLI warnings/errors are now visible by default (logging was previously disabled at import time)

## 0.0.8 - 2025-07-01

### Changed

- updated to latest version of template with copier

### Added

- parsing is now extended to the science header
- now the tool can predict the source of the telementry (SIS vs JANUS)

## 0.0.7 - 2025-05-27

## 0.0.6 - 2024-11-20

### Added

- ability to parse multiple ssmm files from cli
- fix error when an image is empty

## 0.0.5 - 2024-11-20

## 0.0.4 - 2024-11-06

### Fixed

- Improved test and test coverage with a small test suite

## 0.0.3 - 2024-11-06

### Added

- Optional CLI available to get info from command line

## 0.0.2 - 2024-11-05
