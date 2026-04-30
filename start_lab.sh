#!/bin/bash

# VirtualFPGALab: Integrated Launcher
# Usage: ./start_lab.sh [scenario_dir]

SCENARIO_DIR=${1:-"tests/scenarios/01_standard_uio"}
DTS_PATH="${SCENARIO_DIR}/config.dts"

echo "===================================================="
echo "   VirtualFPGALab Integrated Launcher"
echo "   Scenario: ${SCENARIO_DIR}"
echo "===================================================="

# 1. 準備
if [ ! -f "${DTS_PATH}" ]; then
    echo "[Error] DTS file not found: ${DTS_PATH}"
    exit 1
fi

# 2. 生成とビルド
echo "[1/3] Generating code and building artifacts..."
python3 scripts/gen_vfpga.py "${DTS_PATH}" || exit 1

# シナリオ固有のVerilogファイルをコピー
cp ${SCENARIO_DIR}/*.v src/rtl/ 2>/dev/null

# シミュレータのビルド
gcc -Wall -Wextra -fPIC -Isrc/include -shared -ldl -o libfpgashim.so src/shim/libfpgashim.c
# RTL内の全ファイルを対象にする
V_FILES=$(ls src/rtl/*.v)
verilator -Wall --cc --exe -CFLAGS "-I../src/include" ${V_FILES} src/sim/sim_main.cpp > /dev/null 2>&1
make -C obj_dir -f Vvfpga_top.mk > /dev/null 2>&1
cp obj_dir/Vvfpga_top ./vfpga_sim

# アプリケーションのビルド
make -C "${SCENARIO_DIR}" > /dev/null 2>&1

# 3. 起動
echo "[2/3] Starting background processes..."

# ログディレクトリの準備
LOG_DIR="logs"
mkdir -p ${LOG_DIR}

# 終了処理の定義
cleanup() {
    echo ""
    echo "===================================================="
    echo "   Stopping VirtualFPGALab..."
    kill ${CONTROLLER_PID} ${SIM_PID} ${DASHBOARD_PID} 2>/dev/null
    echo "   Cleaning up..."
    # 共有メモリのクリーンアップ（必要に応じて）
    echo "   Done."
    echo "===================================================="
    exit
}

trap cleanup SIGINT SIGTERM

# 各プロセスの起動
python3 -u src/controller/vlogic_controller.py "${DTS_PATH}" > ${LOG_DIR}/controller.log 2>&1 &
CONTROLLER_PID=$!

./vfpga_sim > ${LOG_DIR}/simulator.log 2>&1 &
SIM_PID=$!

node dashboard/server.js > ${LOG_DIR}/dashboard.log 2>&1 &
DASHBOARD_PID=$!

sleep 2

echo "[3/3] All systems GO!"
echo "----------------------------------------------------"
echo "  Web Dashboard : http://localhost:8080"
echo "  UART Console  : localhost:2000 (if enabled)"
echo "----------------------------------------------------"
echo "Press Ctrl+C to stop the lab."

# プロセスの監視（どれかが死んだら終了）
while true; do
    if ! kill -0 ${CONTROLLER_PID} 2>/dev/null || \
       ! kill -0 ${SIM_PID} 2>/dev/null || \
       ! kill -0 ${DASHBOARD_PID} 2>/dev/null; then
        echo "[Warning] One of the processes has stopped."
        cleanup
    fi
    sleep 1
done
