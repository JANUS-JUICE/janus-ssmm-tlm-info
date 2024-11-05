# A variable for the version file
VERSION_FILE := "pyproject.toml"
CHANGELOG := "CHANGELOG.md"

# Default task
default:
    @just --list

# Task to bump the version (major, minor, patch)
bump version_kind:
    @echo "Bumping {{version_kind}} version..."
    poetry run kacl-cli verify
    poetry run bump-my-version bump {{version_kind}} 

    @echo "New version will be: {{`poetry version -s`}}"
    just release-changelog {{`poetry version -s`}}

    # Commit the changes
    git add {{VERSION_FILE}} {{CHANGELOG}}
    git commit -m "Bump version to {{`poetry version -s`}} and update changelog"
    git tag v{{`poetry version -s`}}
    @echo "Version bump and changelog update complete."

# Task to release changelog with the new version
release-changelog version:
    @echo "Releasing changelog for version kind {{version}}..."
    poetry run kacl-cli release  {{version}}  -m --allow-no-changes

# Clean up task (optional)
clean:
    @echo "Cleaning..."
    rm -rf __pycache__ .pytest_cache

@audit:
  poetry run pip-audit
  poetry run deptry -- src tests
  

@download_test_data:
    mkdir -p tests/data/splitted
    scp -i /home/luca/.ssh/Janus-IAPS janus-admin@janus.iaps.inaf.it://data2/JANUS_RAW_ARCHIVE/01_-_FLIGHT/02_-_CRUISE/05_-_LEGA/tlm/01_-_moon/JAN1_37000010_2024.233.14.56.21.608 tests/data/JAN1_37000010_2024.233.14.56.21.608 
    scp -i /home/luca/.ssh/Janus-IAPS janus-admin@janus.iaps.inaf.it://data2/JANUS_RAW_ARCHIVE/01_-_FLIGHT/02_-_CRUISE/05_-_LEGA/tlm/02_-_earth/splitted/JAN2_4700000A_2024.234.16.25.54.129 tests/data/splitted/JAN2_4700000A_2024.234.16.25.54.129
    scp -i /home/luca/.ssh/Janus-IAPS janus-admin@janus.iaps.inaf.it://data2/JANUS_RAW_ARCHIVE/01_-_FLIGHT/02_-_CRUISE/05_-_LEGA/tlm/02_-_earth/splitted/JAN2_4700000B_2024.234.19.25.53.112 tests/data/splitted/JAN2_4700000B_2024.234.19.25.53.112 
    scp -i /home/luca/.ssh/Janus-IAPS janus-admin@janus.iaps.inaf.it://data2/JANUS_RAW_ARCHIVE/01_-_FLIGHT/02_-_CRUISE/05_-_LEGA/tlm/02_-_earth/JAN2_4700000AB_joined tests/data/JAN2_4700000AB_joined 
