# Scenario 06: AXI GPIO

このシナリオでは、Zynq等のFPGAでよく利用される `AXI GPIO` (General Purpose Input/Output) のエミュレーション機能のテストを行います。

## 構成

- **`config.dts`**: AXI GPIOのデバイスツリー定義 (`xlnx,xps-gpio-1.00.a`) が含まれています。ベースアドレス `0x41200000` に配置され、DATA, TRIなどの基本的なレジスタが定義されています。
- **`main.c`**: GPIOレジスタに対してmmapを行い、チャネル1を出力、チャネル2を入力として設定してテストを行うC言語のアプリケーションです。
- **Dashboard**: Node.jsダッシュボード側で、GPIOの状態（入力・出力ピンの値）を視覚的に確認・操作するための機能拡張のテストにも使用されます。
