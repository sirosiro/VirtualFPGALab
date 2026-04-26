#!/bin/bash

# ==============================================================================
# VirtualFPGALab Test Runner
# ==============================================================================
# Usage:
#   ./tests/run_tests.sh           : Run all tests
#   ./tests/run_tests.sh --clean   : Clean build artifacts and logs
#
# To save logs to a file:
#   ./tests/run_tests.sh 2>&1 | tee test_run.log
# ==============================================================================

# --- Configuration ---
PROJECT_ROOT=$(pwd)
CONTROLLER="src/controller/vlogic_controller.py"
SIMULATOR="obj_dir/Vvfpga_top"
SHIM="libfpgashim.so"

# --- Functions ---
cleanup_processes() {
    echo -e "\n[Runner] Stopping background processes..."
    pkill -f vlogic_controller || true
    pkill -f Vvfpga_top || true
}

# --- Argument Parsing ---
if [[ "$1" == "--clean" || "$1" == "-c" ]]; then
    echo "[Runner] Cleaning project artifacts and logs..."
    make clean
    rm -f *.log
    echo "[Runner] Clean finished."
    exit 0
fi

# Ensure processes are stopped on exit if we are running tests
trap cleanup_processes EXIT

# --- Execution ---
echo "[Runner] Building project..."
make -j$(nproc) || exit 1

echo "[Runner] Starting Backend (vlogic_controller.py)..."
python3 $CONTROLLER &
sleep 2

echo "[Runner] Starting Simulator (Vvfpga_top)..."
./$SIMULATOR &
sleep 2

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
