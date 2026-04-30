#!/bin/bash

# VirtualFPGALab: Integrated Launcher
# Usage: ./start_lab.sh [scenario_dir]
unset LD_PRELOAD

SCENARIO_DIR=${1:-"tests/scenarios/01_standard_uio"}
DTS_PATH="${SCENARIO_DIR}/config.dts"

# 実行モードの設定（03シナリオ等での対話モードを有効化）
export VFPGA_INTERACTIVE=1

echo "===================================================="
echo "   VirtualFPGALab Integrated Launcher"
echo "   Scenario: ${SCENARIO_DIR}"
echo "===================================================="

# 1. 準備とクリーンアップ
echo "[0/3] Cleaning up previous state..."
pkill -f vlogic_controller || true
pkill -f Vvfpga_top || true
pkill -f test_bin || true
pkill -f "node dashboard/server.js" || true
rm -f libfpgashim.so
rm -rf obj_dir
rm -f dashboard/data/*.json
rm -f /tmp/vfpga_*
make clean > /dev/null 2>&1 || true

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
rm -f ./vfpga_sim
cp obj_dir/Vvfpga_top ./vfpga_sim

# アプリケーションのビルド
make -C "${SCENARIO_DIR}" > /dev/null 2>&1

# 3. 起動
echo "[2/3] Starting background processes..."

# ログディレクトリの準備
LOG_DIR="logs"
mkdir -p ${LOG_DIR}

# バックエンドプロセスの起動
python3 -u src/controller/vlogic_controller.py "${SCENARIO_DIR}/config.dts" > ${LOG_DIR}/controller.log 2>&1 &
CONTROLLER_PID=$!

obj_dir/Vvfpga_top > ${LOG_DIR}/sim.log 2>&1 &
SIM_PID=$!

node dashboard/server.js > ${LOG_DIR}/dashboard.log 2>&1 &
DASHBOARD_PID=$!

# バックエンドの準備を待機（最大5秒）
# 生成されたヘッダファイルからSHMファイル名を取得する
SHM_FILE_EXPECTED=$(grep -oP '#define SHM_FILE "\\K[^"]+' src/include/vfpga_config.h 2>/dev/null || echo "/tmp/vfpga_reg")

MAX_RETRIES=5
RETRY_COUNT=0
while [ ! -f "$SHM_FILE_EXPECTED" ] && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT+1))
done

echo "[3/3] All systems GO!"
echo "----------------------------------------------------"
echo "  Web Dashboard : http://localhost:8080"
echo "  UART Console  : localhost:2000 (if enabled)"
echo "----------------------------------------------------"
echo "Press Ctrl+C to stop the lab (after app exits)."

# FWアプリケーションの起動（対話モードをサポートするためフォアグラウンドで実行）
echo ""
echo "   Starting firmware application..."
LD_PRELOAD="$PWD/libfpgashim.so" "${SCENARIO_DIR}/test_bin"

# アプリ終了後もバックエンドの状態を監視し続ける
# プロセスの監視
while true; do
    if ! kill -0 ${CONTROLLER_PID} 2>/dev/null || \
       ! kill -0 ${SIM_PID} 2>/dev/null || \
       ! kill -0 ${DASHBOARD_PID} 2>/dev/null; then
        echo "[Warning] One of the processes has stopped."
        cleanup
    fi
    sleep 1
done
