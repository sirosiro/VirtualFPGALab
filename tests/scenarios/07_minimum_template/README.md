# Scenario 07: Minimum Template

このディレクトリは、FPGA-BoardlessBench (F-BB) で新しい回路設計やファームウェア開発を始めるための「最小構成テンプレート」です。

## 構成ファイル (Manifest)

- **vfpga_top.v**: ユーザー回路（RTL）のトップモジュールです。
    - `clk` ポートのみを持つ最小構成からスタートできます。
    - 必要に応じて `addr`, `w_data`, `w_en`, `r_data` ポートを追加してバス通信を実装してください。
- **config.dts**: 仮想ボードの定義ファイル（Device Tree Source）です。
    - `generic-uio` を用いたレジスタアクセス設定が含まれています。
- **main.c**: テスト用のファームウェア（C言語）です。
    - シミュレーションを実行し、波形を生成するための最小限のコードが含まれています。
- **Makefile**: ファームウェアのビルド設定です。
- **run.sh**: このシナリオを即座に実行するためのショートカットスクリプトです。

## 使い方 (Usage)

新しい実験を始めたいときは、この `07_minimum_template` ディレクトリをコピーして新しい番号（例：`08_my_logic`）を作成してください。

```bash
cp -r tests/scenarios/07_minimum_template tests/scenarios/08_my_logic
```

## 実行方法 (Execution)

```bash
./run.sh
```
または、プロジェクトルートから以下を実行します：
```bash
./start_lab.sh tests/scenarios/07_minimum_template/
```

実行後、`vfpga.vcd` が生成されます。GTKWave 等で波形を確認してデバッグを進めてください。
