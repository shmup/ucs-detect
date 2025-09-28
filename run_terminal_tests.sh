#!/bin/bash
# orchestrate terminal testing for ucs-detect

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# default values
METHOD="docker"
TERMINALS=""
RESULTS_DIR="docker-test/results"

# parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --method)
            METHOD="$2"
            shift 2
            ;;
        --terminals)
            TERMINALS="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --help)
            cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --method METHOD        Testing method: docker, native, or python (default: docker)
    --terminals TERMINALS  Comma-separated list of terminals to test (default: all)
    --results-dir DIR      Directory to store results (default: docker-test/results)
    --help                Show this help message

Examples:
    # test all terminals using docker
    $0

    # test specific terminals
    $0 --terminals "xterm,konsole,tmux"

    # use native python tester
    $0 --method python

    # use native testing (requires terminals installed)
    $0 --method native
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# create results directory
mkdir -p "$RESULTS_DIR"

echo "Terminal Testing for ucs-detect"
echo "================================"
echo "Method: $METHOD"
echo "Results directory: $RESULTS_DIR"
echo ""

case "$METHOD" in
    docker)
        echo "Using Docker-based testing..."
        echo ""

        # build base image
        echo "Building Docker test image..."
        docker build -f docker-test/Dockerfile.test-base -t ucs-detect-test-base .

        if [ -z "$TERMINALS" ]; then
            # test all terminals
            echo "Testing all available terminals..."
            docker-compose -f docker-test/docker-compose.test.yml up test-all

            # aggregate results
            echo ""
            echo "Aggregating results..."
            docker-compose -f docker-test/docker-compose.test.yml up aggregate-results
        else
            # test specific terminals
            IFS=',' read -ra TERMINAL_ARRAY <<< "$TERMINALS"
            for terminal in "${TERMINAL_ARRAY[@]}"; do
                echo "Testing $terminal..."
                docker run --rm \
                    -v "$PWD/$RESULTS_DIR:/results" \
                    -v "$PWD:/app" \
                    -e "TERMINAL=$terminal" \
                    -e "OUTPUT_DIR=/results" \
                    ucs-detect-test-base \
                    /usr/local/bin/run_terminal_test.sh || true
                sleep 2
            done

            # aggregate results
            echo ""
            echo "Aggregating results..."
            docker run --rm \
                -v "$PWD/$RESULTS_DIR:/results" \
                -v "$PWD:/app" \
                ucs-detect-test-base \
                python3 /app/docker-test/aggregate_results.py
        fi
        ;;

    python)
        echo "Using Python-based testing..."
        if [ ! -f "test_terminals.py" ]; then
            echo "Error: test_terminals.py not found"
            exit 1
        fi

        if [ -z "$TERMINALS" ]; then
            python3 test_terminals.py --output-dir "$RESULTS_DIR"
        else
            IFS=',' read -ra TERMINAL_ARRAY <<< "$TERMINALS"
            python3 test_terminals.py --output-dir "$RESULTS_DIR" --terminals "${TERMINAL_ARRAY[@]}"
        fi
        ;;

    native)
        echo "Using native terminal testing..."
        echo "This requires terminals to be installed locally."
        echo ""

        if [ -z "$TERMINALS" ]; then
            TERMINALS="xterm,konsole,gnome-terminal,kitty,alacritty,tmux,screen"
        fi

        IFS=',' read -ra TERMINAL_ARRAY <<< "$TERMINALS"
        for terminal in "${TERMINAL_ARRAY[@]}"; do
            echo "Testing $terminal..."

            # check if terminal exists
            if ! command -v "$terminal" &> /dev/null; then
                echo "  $terminal not found, skipping..."
                continue
            fi

            OUTPUT_FILE="$RESULTS_DIR/${terminal}_$(date +%Y%m%d_%H%M%S).yaml"

            case "$terminal" in
                xterm|rxvt*)
                    timeout 30 $terminal -e "ucs-detect --save-yaml=$OUTPUT_FILE --quick" || true
                    ;;
                konsole)
                    timeout 30 konsole -e "ucs-detect --save-yaml=$OUTPUT_FILE --quick" || true
                    ;;
                gnome-terminal)
                    timeout 30 gnome-terminal -- bash -c "ucs-detect --save-yaml=$OUTPUT_FILE --quick" || true
                    ;;
                kitty)
                    timeout 30 kitty sh -c "ucs-detect --save-yaml=$OUTPUT_FILE --quick" || true
                    ;;
                alacritty)
                    timeout 30 alacritty -e sh -c "ucs-detect --save-yaml=$OUTPUT_FILE --quick" || true
                    ;;
                tmux)
                    tmux new-session -d -s ucs-test "ucs-detect --save-yaml=$OUTPUT_FILE --quick"
                    sleep 10
                    tmux kill-session -t ucs-test || true
                    ;;
                screen)
                    screen -d -m -S ucs-test sh -c "ucs-detect --save-yaml=$OUTPUT_FILE --quick"
                    sleep 10
                    screen -X -S ucs-test quit || true
                    ;;
            esac

            if [ -f "$OUTPUT_FILE" ]; then
                echo "  ✓ Results saved"
            else
                echo "  ✗ Test failed"
            fi

            sleep 2
        done

        # aggregate results
        echo ""
        echo "Aggregating results..."
        python3 docker-test/aggregate_results.py --results-dir "$RESULTS_DIR"
        ;;

    *)
        echo "Unknown method: $METHOD"
        echo "Valid methods: docker, python, native"
        exit 1
        ;;
esac

echo ""
echo "Testing complete!"
echo "Results are in: $RESULTS_DIR"

# show summary if aggregate report exists
if [ -f "$RESULTS_DIR/aggregate_report.json" ]; then
    echo ""
    echo "Summary:"
    python3 -c "
import json
with open('$RESULTS_DIR/aggregate_report.json') as f:
    data = json.load(f)
    print(f\"  Terminals tested: {data['terminals_tested']}\")
    print(f\"  Terminal list: {', '.join(data['terminal_list'])}\")
"
fi