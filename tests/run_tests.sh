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

# --- Main Test Execution ---

# Build all tests once
make -C tests
# --- Execution Functions ---
run_test() {
    local test_bin=$1
    echo -e "\n>> Running ${test_bin}..."
    LD_PRELOAD=./${SHIM} ./${test_bin}
    local status=$?
    if [ $status -ne 0 ]; then
        echo "<< ${test_bin}: FAIL"
        cleanup_processes
        exit 1
    fi
    echo "<< ${test_bin}: PASS"
}

start_environment() {
    local dts=$1
    echo "[Runner] Setting up environment with ${dts}..."
    
    # 1. Generate code from DTS
    python3 scripts/gen_vfpga.py ${dts}
    
    # 2. Rebuild Shim and Simulator (ensure they match the DTS)
    make libfpgashim.so -j$(nproc)
    make engine -j$(nproc)
    
    # 3. Start Controller
    python3 -u ${CONTROLLER} ${dts} > controller.log 2>&1 &
    
    # 4. Start Simulator
    ./${SIMULATOR} > simulator.log 2>&1 &
    
    # Wait for startup
    sleep 3
    
    # Check if alive
    if ! pgrep -f vlogic_controller > /dev/null; then
        echo "[Runner] ERROR: Controller failed to start. See controller.log"
        cat controller.log
        exit 1
    fi
    if ! pgrep -f Vvfpga_top > /dev/null; then
        echo "[Runner] ERROR: Simulator failed to start. See simulator.log"
        cat simulator.log
        exit 1
    fi
}

# --- Main Test Execution ---

# Build all tests once
make -C tests

# PHASE 1: Standard UIO Tests
start_environment "tests/vfpga_config.dts"

run_test "tests/test_open"
run_test "tests/test_shm"
run_test "tests/test_reg_access"
run_test "tests/test_i2c"
run_test "tests/test_verilator"
run_test "tests/test_multi_i2c"
run_test "tests/test_uart"

cleanup_processes

# PHASE 2: /dev/mem Intercept Tests
start_environment "tests/vfpga_config_devmem.dts"

run_test "tests/test_dev_mem"
run_test "tests/test_multi_i2c"
run_test "tests/test_legacy_style"

cleanup_processes

echo -e "\n[Runner] ALL TESTS PASSED SUCCESSFULLY!"

if [ "$INTERACTIVE" = true ]; then
    echo -e "\n[Runner] INTERACTIVE MODE: Environment is being maintained."
    echo "[Runner] You can access the dashboard at http://127.0.0.1:8080"
    echo "[Runner] Press Enter to stop and cleanup..."
    read
fi
