# Automated Terminal Testing for ucs-detect

This document describes the automated terminal testing infrastructure for ucs-detect, which allows testing Unicode support across multiple terminal emulators in isolated Docker environments.

## Overview

The automated testing system runs ucs-detect across different terminal emulators and aggregates the results for comparison. It supports both GUI terminals (using Xvfb) and text-mode terminals (tmux, screen).

## Quick Start

### Test a Single Terminal

```bash
# Build the minimal test image
docker build -f docker-test/Dockerfile.minimal -t ucs-detect-minimal .

# Test tmux
docker run --rm -v "$(pwd)/docker-test/results:/results" \
  -e TERMINAL=tmux -e OUTPUT_DIR=/results ucs-detect-minimal

# Test screen
docker run --rm -v "$(pwd)/docker-test/results:/results" \
  -e TERMINAL=screen -e OUTPUT_DIR=/results ucs-detect-minimal
```

### Run Multiple Tests with Orchestration

```bash
# Test specific terminals
./run_terminal_tests.sh --terminals "tmux,screen"

# Test all available terminals (when GUI support is added)
./run_terminal_tests.sh

# Use native method (requires terminals installed locally)
./run_terminal_tests.sh --method native --terminals "tmux,screen"
```

### Using Docker Compose

```bash
# Test individual terminals
docker-compose -f docker-test/docker-compose.test.yml up test-tmux
docker-compose -f docker-test/docker-compose.test.yml up test-screen

# Test all terminals sequentially
docker-compose -f docker-test/docker-compose.test.yml up test-all

# Aggregate results
docker-compose -f docker-test/docker-compose.test.yml up aggregate-results
```

## Architecture

### Core Components

1. **`docker-test/Dockerfile.minimal`** - Lightweight Docker image with essential terminals
2. **`docker-test/run_terminal_test.sh`** - Main testing script that runs ucs-detect in different terminals
3. **`docker-test/aggregate_results.py`** - Analysis script that compares results across terminals
4. **`run_terminal_tests.sh`** - Orchestration script for running multiple tests
5. **`docker-test/docker-compose.test.yml`** - Docker Compose configuration for coordinated testing

### Testing Methods

The system supports three testing approaches:

1. **Docker** (recommended) - Isolated, reproducible environments
2. **Native** - Uses locally installed terminals
3. **Python** - Uses the `test_terminals.py` script for automation

### File Structure

```
docker-test/
├── Dockerfile.minimal          # Lightweight test image
├── Dockerfile.test-base        # Full test image (GUI terminals)
├── run_terminal_test.sh        # Core testing script
├── aggregate_results.py        # Results analysis
├── docker-compose.test.yml     # Docker Compose config
└── results/                    # Output directory for test results

run_terminal_tests.sh           # Main orchestration script
test_terminals.py              # Python-based testing script
terminal_testing_approaches.md # Design documentation
```

## Supported Terminals

### Currently Working
- **tmux** - Terminal multiplexer (no display required)
- **screen** - Terminal multiplexer (no display required)

### Planned (GUI terminals requiring Xvfb)
- **xterm** - Standard X terminal
- **konsole** - KDE terminal
- **gnome-terminal** - GNOME terminal
- **rxvt-unicode** - Lightweight terminal
- **kitty** - Modern terminal emulator
- **alacritty** - GPU-accelerated terminal

## Output Format

### Individual Test Results

Each test generates a YAML file with comprehensive Unicode support data:

```yaml
datetime: 2025-09-28 21:04:39 UTC
software: tmux
version: automated-test
system: Linux
python_version: 3.10.12
seconds_elapsed: 0.197
test_results:
  unicode_wide_version: "15.0.0"
  unicode_wide_results:
    # Wide character test results by Unicode version
  emoji_zwj_results:
    # Zero-Width Joiner sequence results
  emoji_vs16_results:
    # Variation Selector-16 results
  language_results:
    # Language support results (null for --quick tests)
```

### Aggregated Results

The aggregation script produces:

1. **Console summary** - Comparison table with failure counts
2. **JSON report** (`aggregate_report.json`) - Machine-readable analysis
3. **Markdown report** (`terminal_report.md`) - Human-readable documentation

Example console output:
```
Terminal             VS16       ZWJ        Wide       Total
------------------------------------------------------------
tmux                 50         0          0          50
screen               50         0          0          50

Best Unicode Support (fewest failures):
  1. tmux: 50 failures
  2. screen: 50 failures
```

## Configuration

### Environment Variables

- `TERMINAL` - Terminal emulator to test (default: xterm)
- `OUTPUT_DIR` - Directory for results (default: ./results)

### Command Line Options

The testing relies on ucs-detect's CLI options:

- `--quick` - Fast testing mode (limits codepoints and skips language tests)
- `--software <name>` - Terminal software name (avoids interactive prompt)
- `--version <version>` - Terminal version (avoids interactive prompt)
- `--save-yaml <file>` - Save results to YAML file

### Testing Parameters

Default settings for automated testing:
- Software name: Uses the `$TERMINAL` environment variable
- Version: `"automated-test"`
- Mode: Always uses `--quick` for faster execution
- Timeout: 60 seconds per test
- Results format: YAML

## Implementation Details

### Terminal-Specific Handling

Each terminal type requires different launching mechanisms:

```bash
# tmux/screen (no display)
tmux new-session -d -s "session" "ucs-detect --save-yaml=file.yaml --quick --software=tmux --version=automated-test"

# GUI terminals (requires Xvfb)
xterm -e sh -c "ucs-detect --save-yaml=file.yaml --quick --software=xterm --version=automated-test"
```

### Error Handling

- **Timeout protection** - Tests automatically terminate after 60 seconds
- **Process cleanup** - Terminal sessions are properly killed on completion
- **File validation** - Verifies YAML output was created successfully
- **Locale support** - Ensures proper UTF-8 locale in containers

### Performance Optimizations

1. **Layered Docker builds** - Base dependencies cached between runs
2. **Minimal image** - Only essential packages for faster builds
3. **Quick testing mode** - Reduced codepoint limits for development
4. **Parallel execution** - Multiple terminals can be tested simultaneously

## Troubleshooting

### Common Issues

1. **Locale errors** - Ensure `locales` package is installed and `en_US.UTF-8` is generated
2. **Display issues** - GUI terminals require proper Xvfb setup with available display numbers
3. **Timeout failures** - Increase timeout values for slower environments
4. **File permissions** - Results directory must be writable by container

### Debug Commands

```bash
# Test ucs-detect directly in container
docker run --rm ucs-detect-minimal ucs-detect --help

# Check container locale
docker run --rm ucs-detect-minimal locale

# Test terminal availability
docker run --rm ucs-detect-minimal tmux -V
docker run --rm ucs-detect-minimal screen -v
```

### Logs and Debugging

- Terminal sessions log their completion status
- Failed tests show expected vs actual file paths
- Aggregation script shows which results were loaded
- Docker build logs show package installation progress

## Future Enhancements

### Planned Features

1. **GUI Terminal Support** - Complete Xvfb integration for graphical terminals
2. **CI/CD Integration** - GitHub Actions workflow for automated testing
3. **Historical Tracking** - Database storage and trend analysis
4. **Performance Metrics** - Test execution time and resource usage
5. **Custom Test Profiles** - Different test configurations (quick, full, specific features)

### Scalability Improvements

1. **Multi-architecture builds** - ARM64 and x86_64 support
2. **Kubernetes deployment** - Distributed testing across clusters
3. **Results database** - PostgreSQL/MongoDB storage for large datasets
4. **Web dashboard** - Real-time results visualization
5. **Regression detection** - Automated alerts for Unicode support changes

## Contributing

### Adding New Terminals

1. Update `docker-test/Dockerfile.minimal` with terminal installation
2. Add terminal-specific launch logic to `run_terminal_test.sh`
3. Update `docker-test/docker-compose.test.yml` with new service
4. Test the terminal with both Docker and native methods

### Extending Analysis

The aggregation script can be enhanced with:
- Additional metrics calculation
- Custom scoring algorithms
- Export formats (CSV, XML, etc.)
- Integration with external reporting tools

For detailed implementation examples, see `terminal_testing_approaches.md`.