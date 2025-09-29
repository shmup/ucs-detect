#!/bin/bash
# run terminal test with xvfb

set -e

TERMINAL="${TERMINAL:-xterm}"
OUTPUT_DIR="${OUTPUT_DIR:-./results}"

echo "Testing terminal: $TERMINAL"

# create output directory
mkdir -p "$OUTPUT_DIR"

# generate output filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/${TERMINAL}_${TIMESTAMP}.yaml"

# use absolute paths to avoid path issues
ABS_OUTPUT_FILE="$(cd "$(dirname "$OUTPUT_FILE")" && pwd)/$(basename "$OUTPUT_FILE")"

# check if ucs-detect is available
if ! command -v ucs-detect &> /dev/null; then
    echo "ERROR: ucs-detect not found in PATH"
    exit 1
fi

# run test based on terminal type
case "$TERMINAL" in
    xterm|rxvt*)
        # find available display
        for i in {99..110}; do
            if ! [ -e /tmp/.X${i}-lock ]; then
                DISPLAY_NUM=$i
                break
            fi
        done

        if [ -z "$DISPLAY_NUM" ]; then
            echo "No available display found"
            exit 1
        fi

        echo "Starting Xvfb on display :$DISPLAY_NUM"
        Xvfb :$DISPLAY_NUM -screen 0 1024x768x24 &
        XVFB_PID=$!
        export DISPLAY=:$DISPLAY_NUM
        sleep 3

        echo "Launching $TERMINAL with ucs-detect..."
        # Run xterm in background and wait for file to appear
        $TERMINAL -e sh -c "ucs-detect --save-yaml='$ABS_OUTPUT_FILE' --quick --software='$TERMINAL' --version='automated-test'; echo 'DONE' > '$ABS_OUTPUT_FILE.done'" &
        TERM_PID=$!

        # Wait for completion (up to 60 seconds)
        for i in {1..60}; do
            if [ -f "$ABS_OUTPUT_FILE.done" ]; then
                echo "Test completed after ${i} seconds"
                break
            fi
            sleep 1
        done

        # Cleanup
        kill $TERM_PID 2>/dev/null || true
        kill $XVFB_PID 2>/dev/null || true
        rm -f "$ABS_OUTPUT_FILE.done"
        ;;

    konsole)
        # Similar to xterm but with konsole syntax
        for i in {99..110}; do
            if ! [ -e /tmp/.X${i}-lock ]; then
                DISPLAY_NUM=$i
                break
            fi
        done

        echo "Starting Xvfb on display :$DISPLAY_NUM"
        Xvfb :$DISPLAY_NUM -screen 0 1024x768x24 &
        XVFB_PID=$!
        export DISPLAY=:$DISPLAY_NUM
        sleep 3

        konsole -e sh -c "ucs-detect --save-yaml='$ABS_OUTPUT_FILE' --quick --software='$TERMINAL' --version='automated-test'; echo 'DONE' > '$ABS_OUTPUT_FILE.done'" &
        TERM_PID=$!

        for i in {1..60}; do
            if [ -f "$ABS_OUTPUT_FILE.done" ]; then
                break
            fi
            sleep 1
        done

        kill $TERM_PID 2>/dev/null || true
        kill $XVFB_PID 2>/dev/null || true
        rm -f "$ABS_OUTPUT_FILE.done"
        ;;

    gnome-terminal)
        for i in {99..110}; do
            if ! [ -e /tmp/.X${i}-lock ]; then
                DISPLAY_NUM=$i
                break
            fi
        done

        echo "Starting Xvfb on display :$DISPLAY_NUM"
        Xvfb :$DISPLAY_NUM -screen 0 1024x768x24 &
        XVFB_PID=$!
        export DISPLAY=:$DISPLAY_NUM
        sleep 3

        gnome-terminal -- sh -c "ucs-detect --save-yaml='$ABS_OUTPUT_FILE' --quick --software='$TERMINAL' --version='automated-test'; echo 'DONE' > '$ABS_OUTPUT_FILE.done'" &
        TERM_PID=$!

        for i in {1..60}; do
            if [ -f "$ABS_OUTPUT_FILE.done" ]; then
                break
            fi
            sleep 1
        done

        kill $TERM_PID 2>/dev/null || true
        kill $XVFB_PID 2>/dev/null || true
        rm -f "$ABS_OUTPUT_FILE.done"
        ;;

    tmux)
        echo "Testing with tmux (no display needed)..."
        # tmux doesn't need display
        unset DISPLAY

        tmux new-session -d -s "ucs-test-$$" "ucs-detect --save-yaml='$ABS_OUTPUT_FILE' --quick --software='$TERMINAL' --version='automated-test'"

        # Wait for session to complete (up to 60 seconds)
        for i in {1..60}; do
            if ! tmux has-session -t "ucs-test-$$" 2>/dev/null; then
                echo "tmux session completed after ${i} seconds"
                break
            fi
            if [ -f "$ABS_OUTPUT_FILE" ]; then
                echo "Output file created after ${i} seconds"
                break
            fi
            sleep 1
        done

        # Cleanup session if still running
        tmux kill-session -t "ucs-test-$$" 2>/dev/null || true
        ;;

    screen)
        echo "Testing with screen (no display needed)..."
        # screen doesn't need display
        unset DISPLAY
        SESSION_NAME="ucs-test-$$"

        screen -d -m -S "$SESSION_NAME" sh -c "ucs-detect --save-yaml='$ABS_OUTPUT_FILE' --quick --software='$TERMINAL' --version='automated-test'"

        # Wait for completion
        for i in {1..60}; do
            if ! screen -list | grep -q "$SESSION_NAME"; then
                echo "screen session completed after ${i} seconds"
                break
            fi
            if [ -f "$ABS_OUTPUT_FILE" ]; then
                echo "Output file created after ${i} seconds"
                break
            fi
            sleep 1
        done

        # Cleanup
        screen -X -S "$SESSION_NAME" quit 2>/dev/null || true
        ;;

    *)
        echo "Unknown terminal: $TERMINAL"
        exit 1
        ;;
esac

# check if output was created
if [ -f "$ABS_OUTPUT_FILE" ]; then
    echo "Test completed successfully!"
    echo "Results saved to: $ABS_OUTPUT_FILE"
    echo "File size: $(wc -l < "$ABS_OUTPUT_FILE") lines"
    echo "First few lines:"
    head -10 "$ABS_OUTPUT_FILE"
else
    echo "Test failed - no output file generated"
    echo "Expected file: $ABS_OUTPUT_FILE"
    echo "Directory contents:"
    ls -la "$OUTPUT_DIR" || echo "Output directory doesn't exist"
    exit 1
fi