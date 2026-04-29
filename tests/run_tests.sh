#!/bin/bash

export LC_ALL=C
export LANG=C

# ==============================================================================
# VirtualFPGALab Test Runner (Scenario-Based)
# ==============================================================================
# Usage:
#   ./tests/run_tests.sh           : Run all scenarios
#   ./tests/run_tests.sh --clean   : Clean build artifacts and logs
#   ./tests/run_tests.sh --interactive : Run tests and keep environment
# ==============================================================================

# --- Configuration ---
PROJECT_ROOT=$(pwd)
CONTROLLER="src/controller/vlogic_controller.py"
SIMULATOR="obj_dir/Vvfpga_top"
SHIM="libfpgashim.so"
SCENARIOS_DIR="tests/scenarios"

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
    rm -f tests/scenarios/*/test_bin tests/scenarios/*/*.bin
    for scenario in tests/scenarios/*; do
        if [ -f "${scenario}/Makefile" ]; then
            make -C "${scenario}" clean > /dev/null 2>&1 || true
        fi
    done
    rm -f tests/scenarios/*/*.log
    rm -f *.log
    echo "[Runner] Clean finished."
    exit 0
fi

trap cleanup_processes EXIT

start_environment() {
    local scenario_dir=$1
    local dts="${scenario_dir}/config.dts"
    echo -e "\n[Runner] >>> SCENARIO: $(basename ${scenario_dir}) <<<"

    # 前のシナリオの残骸を削除し、クリーンな状態にする
    make clean > /dev/null 2>&1

    echo "[Runner] Setting up environment with ${dts}..."
    
    # 1. Generate code from DTS
    python3 scripts/gen_vfpga.py ${dts}
    
    # 2. Handle Verilog
    # シナリオディレクトリにある全ての .v ファイルを src/rtl/ にコピーする
    if ls "${scenario_dir}/"*.v >/dev/null 2>&1; then
        echo "[Runner] Copying Verilog files from scenario..."
        cp "${scenario_dir}/"*.v src/rtl/
    fi

    # vfpga_top.v が存在しない場合はスケルトンを使用する
    if [ ! -f "src/rtl/vfpga_top.v" ]; then
        echo "[Runner] vfpga_top.v not found. Using default RTL skeleton."
        cp src/rtl/vfpga_top_skeleton.v src/rtl/vfpga_top.v
    fi

    # 重複を避けるため、スケルトンファイルは削除しておく
    rm -f src/rtl/vfpga_top_skeleton.v
    
    make libfpgashim.so -j$(nproc) || exit 1
    make engine -j$(nproc) || exit 1
    
    # 3. Start Controller
    python3 -u ${CONTROLLER} ${dts} > "${scenario_dir}/controller.log" 2>&1 &
    
    # 4. Start Simulator
    ./${SIMULATOR} > "${scenario_dir}/simulator.log" 2>&1 &
    
    sleep 3
}

# --- Main Execution ---

for scenario in ${SCENARIOS_DIR}/*; do
    if [ ! -d "${scenario}" ]; then continue; fi
    
    start_environment "${scenario}"
    
    # Build the scenario via Makefile
    echo "[Runner] Building ${scenario} via Makefile..."
    make -C "${scenario}" || exit 1
    
    # Run the test
    echo "[Runner] Running test..."
    LD_PRELOAD=./${SHIM} ./${scenario}/test_bin
    
    if [ $? -eq 0 ]; then
        echo "[Runner] RESULT: $(basename ${scenario}) PASSED"
    else
        echo "[Runner] RESULT: $(basename ${scenario}) FAILED"
        exit 1
    fi
    
    if [ "$INTERACTIVE" = false ]; then
        cleanup_processes
    else
        echo "[Runner] INTERACTIVE MODE: Environment is being maintained."
        echo "[Runner] Press Enter to continue to next scenario (or stop)..."
        read
        cleanup_processes
    fi
done

echo -e "\n[Runner] ALL SCENARIOS COMPLETED SUCCESSFULLY!"
