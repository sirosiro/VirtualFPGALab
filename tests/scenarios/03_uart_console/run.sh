#!/bin/bash
# F-BB: 03_uart_console 実行スクリプト
# このスクリプトを叩くだけで、このディレクトリの環境が立ち上がりテストが実行されます。
# オプション: --clean (または -c) で成果物を削除します。

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
"$SCRIPT_DIR/../../scenario_runner.sh" "$SCRIPT_DIR" "$@"
