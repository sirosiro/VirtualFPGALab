#!/bin/bash

# ==============================================================================
# F-BB Scenario Runner (Shared Infrastructure)
# ==============================================================================
# このスクリプトは、個別のテストシナリオを実行するための共通ロジックです。
# 1. DTSからのコード生成 2. シミュレーションエンジンのビルド 3. バックグラウンド起動
# 4. アプリケーションのコンパイルと実行 5. プロセスの自動クリーンアップ
# を行います。
# ==============================================================================

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
SCENARIO_PATH=""
CLEAN=false

# --- 引数解析 ---
for arg in "$@"; do
    case $arg in
        --clean|-c) CLEAN=true ;;
        *) if [ -d "$arg" ]; then SCENARIO_PATH="$arg"; fi ;;
    esac
done

if [ -z "$SCENARIO_PATH" ]; then
    echo "Usage: $0 <scenario_directory_path> [--clean|-c]"
    exit 1
fi

# シナリオの絶対パスを取得
SCENARIO_DIR=$(cd "$SCENARIO_PATH" && pwd)
SCENARIO_NAME=$(basename "$SCENARIO_DIR")

# --- クリーンアップモード ---
if [ "$CLEAN" = true ]; then
    echo "[Runner] Cleaning artifacts for scenario: ${SCENARIO_NAME}..."
    cd "${PROJECT_ROOT}"
    make clean > /dev/null 2>&1 || true
    if [ -f "${SCENARIO_DIR}/Makefile" ]; then
        make -C "${SCENARIO_DIR}" clean > /dev/null 2>&1 || true
    fi
    rm -f "${SCENARIO_DIR}/"*.log
    rm -f "${PROJECT_ROOT}/controller.log" "${PROJECT_ROOT}/simulator.log"
    echo "[Runner] Clean finished."
    exit 0
fi

# --- 設定 ---
CONTROLLER="${PROJECT_ROOT}/src/controller/vlogic_controller.py"
SIMULATOR="${PROJECT_ROOT}/obj_dir/Vvfpga_top"
SHIM="${PROJECT_ROOT}/libfpgashim.so"
DTS="${SCENARIO_DIR}/config.dts"

# --- プロセス掃除関数 ---
cleanup() {
    echo -e "\n[Runner] Stopping background processes..."
    pkill -f vlogic_controller || true
    pkill -f Vvfpga_top || true
    pkill -f "node dashboard/server.js" || true
}

# 異常終了時や中断時（Ctrl+C）にプロセスを掃除するように設定
trap cleanup EXIT

# --- 実行フェーズ ---

# 確実にプロジェクトルートから実行を開始する
cd "${PROJECT_ROOT}"

echo -e "\n[Runner] >>> Starting Scenario: ${SCENARIO_NAME} <<<"

# 1. DTSからコード生成
echo "[Runner] Generating code from ${DTS}..."
python3 "${PROJECT_ROOT}/scripts/gen_vfpga.py" "${DTS}"

# 2. Verilogの配置
# シナリオディレクトリにある全ての .v ファイルを src/rtl/ にコピーする
if ls "${SCENARIO_DIR}/"*.v >/dev/null 2>&1; then
    echo "[Runner] Copying Verilog files from scenario..."
    cp "${SCENARIO_DIR}/"*.v "${PROJECT_ROOT}/src/rtl/"
fi

# vfpga_top.v が存在しない場合はスケルトンを使用する
if [ ! -f "${PROJECT_ROOT}/src/rtl/vfpga_top.v" ]; then
    echo "[Runner] vfpga_top.v not found. Using default RTL skeleton."
    cp "${PROJECT_ROOT}/src/rtl/vfpga_top_skeleton.v" "${PROJECT_ROOT}/src/rtl/vfpga_top.v"
fi

# 重複を避けるため、スケルトンファイルは削除しておく
# (vfpga_top.v としてコピーされているか、あるいは不要なため)
rm -f "${PROJECT_ROOT}/src/rtl/vfpga_top_skeleton.v"

# 3. エンジンのビルド
echo "[Runner] Building simulation engine (this may take a few seconds)..."
cd "${PROJECT_ROOT}"
make engine -j$(nproc) || exit 1

# 4. バックグラウンドプロセスの起動
echo "[Runner] Starting Backend Controller & RTL Simulator..."
python3 -u "${CONTROLLER}" "${DTS}" > "${SCENARIO_DIR}/controller.log" 2>&1 &
"${SIMULATOR}" > "${SCENARIO_DIR}/simulator.log" 2>&1 &

# 通信の準備が整うまで少し待機
sleep 2

# 5. アプリケーションのビルド
echo "[Runner] Building application via Makefile in ${SCENARIO_DIR}..."
make -C "${SCENARIO_DIR}" || exit 1

# 6. アプリケーションの実行 (LD_PRELOADを使用)
echo "[Runner] Executing application with LD_PRELOAD..."
cd "${SCENARIO_DIR}"
LD_PRELOAD="${SHIM}" ./test_bin

# 結果を保持
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo -e "\n[Runner] RESULT: SUCCESS"
else
    echo -e "\n[Runner] RESULT: FAILURE (Exit Code: $RESULT)"
    echo "[Runner] Check controller.log and simulator.log in the scenario directory for details."
fi

exit $RESULT
