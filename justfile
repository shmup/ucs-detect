# justfile for ucs-detect project
# Run with: just <command>

# Install in development mode
install:
    pip install -e .

# Run basic Unicode detection test
run:
    ucs-detect

# Run quick test for development (much faster)
quick:
    ucs-detect --quick

# Export UNICODE_VERSION shell variable
shell:
    ucs-detect --shell --quick

# Run detailed test with saved YAML results
test-full limit="5000":
    ucs-detect --save-yaml=results.yaml --limit-codepoints={{limit}}

# Build Sphinx documentation
docs:
    ./make_docs.sh

# Generate results documentation from data files
docs-results:
    python make_results_rst.py

# Generate all Unicode data tables
tables: table-zwj table-vs16 table-wide

# Generate ZWJ sequences table
table-zwj:
    python make_table_zwj.py

# Generate Variation Selector-16 table
table-vs16:
    python make_vs16_table.py

# Generate Wide characters table
table-wide:
    python make_wide_table.py

# Show help
help:
    ucs-detect --help

# Development setup - install and run quick test
dev: install quick

# Clean build artifacts
clean:
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -delete

# Docker commands

# Build Docker image
docker-build:
    docker compose build

# Run ucs-detect in Docker
docker-run *args="--help":
    docker compose run --rm --remove-orphans ucs-detect ucs-detect {{args}}

# Run quick test in Docker
docker-quick:
    docker compose run --rm --remove-orphans ucs-detect ucs-detect --quick

# Open shell in Docker container
docker-shell:
    docker compose run --rm --remove-orphans ucs-detect /bin/bash

# Run full test suite in Docker
docker-test limit="5000":
    docker compose run --rm --remove-orphans ucs-detect ucs-detect --save-yaml=results.yaml --limit-codepoints={{limit}}

# Generate documentation in Docker
docker-docs:
    docker compose up --remove-orphans docs

# Generate Unicode tables in Docker
docker-tables:
    docker compose up --remove-orphans tables

# Clean up Docker containers and images
docker-clean:
    docker compose down --remove-orphans
    docker compose rm -f