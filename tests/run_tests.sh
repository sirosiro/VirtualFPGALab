#!/bin/bash

# ==============================================================================
# VirtualFPGALab Test Runner
# ==============================================================================
# Usage:
#   ./tests/run_tests.sh           : Run all tests
#   ./tests/run_tests.sh --clean   : Clean build artifacts and logs
#   ./tests/run_tests.sh --interactive : Run tests and keep environment for Dashboard
#
# To save logs to a file:
#   ./tests/run_tests.sh 2>&1 | tee test_run.log
# ==============================================================================

# --- Configuration ---
PROJECT_ROOT=$(pwd)
CONTROLLER="src/controller/vlogic_controller.py"
DASHBOARD="src/controller/dashboard_server.py"
SIMULATOR="obj_dir/Vvfpga_top"
SHIM="libfpgashim.so"

# --- Functions ---
cleanup_processes() {
    echo -e "\n[Runner] Stopping background processes..."
    pkill -f vlogic_controller || true
    pkill -f Vvfpga_top || true
    pkill -f dashboard_server || true
}

# --- Argument Parsing ---
CLEAN=false
INTERACTIVE=false

for arg in "$@"; do
    case $arg in
        --clean|-c) CLEAN=true ;;
        --interactive|-i) INTERACTIVE=true ;;
    esac
done

if [ "$CLEAN" = true ]; then
    echo "[Runner] Cleaning project artifacts and logs..."
    make clean
    make -C tests clean
    rm -f *.log
    echo "[Runner] Clean finished."
    exit 0
fi

# Ensure processes are stopped on exit if we are running tests
trap cleanup_processes EXIT

# --- Execution ---
echo "[Runner] Building engine..."
make -j$(nproc) || exit 1
echo "[Runner] Building tests..."
make -C tests -j$(nproc) || exit 1

echo "[Runner] Starting Backend (vlogic_controller.py)..."
python3 $CONTROLLER &
sleep 2

echo "[Runner] Starting Simulator (Vvfpga_top)..."
./$SIMULATOR &
sleep 2

if [ "$INTERACTIVE" = true ]; then
    echo "[Runner] Starting Dashboard (dashboard_server.py) on port 8080..."
    python3 $DASHBOARD &
    sleep 2
    echo "[Runner] Dashboard is ready at http://127.0.0.1:8080"
fi

# Check if background processes are alive
if ! pgrep -f vlogic_controller > /dev/null; then
    echo "[Runner] ERROR: Backend failed to start."
    exit 1
fi

# --- Run Tests ---
echo "[Runner] Starting test suite..."

export LD_PRELOAD=./$SHIM

run_test() {
    local test_bin=$1
    echo -e "\n>> Running $test_bin..."
    ./$test_bin
    if [ $? -eq 0 ]; then
        echo "<< $test_bin: PASS"
    else
        echo "<< $test_bin: FAIL"
        exit 1
    fi
}

run_test "tests/test_open"
run_test "tests/test_shm"
run_test "tests/test_reg_access"
run_test "tests/test_i2c"
run_test "tests/test_verilator"

echo -e "\n[Runner] ALL TESTS PASSED SUCCESSFULLY!"

if [ "$INTERACTIVE" = true ]; then
    echo -e "\n[Runner] INTERACTIVE MODE: Environment is being maintained."
    echo "[Runner] You can access the dashboard at http://127.0.0.1:8080"
    echo "[Runner] Press Enter to stop and cleanup..."
    read
fi
