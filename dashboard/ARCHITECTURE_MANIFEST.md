# dashboard/ ARCHITECTURE_MANIFEST.md

## 1. 存在意義 (Core Value)
`dashboard/` は、物理的な計測器（オシロスコープ、ロジックアナライザ、シリアルコンソール）の仮想的な代替を提供し、学習者がハードウェアの内部状態を非侵襲的かつ直感的に把握できる **UX（ユーザー体験）の要** である。

## 2. 設計原則 (Design Principles)

### 2.1 Decoupled Observability (非侵襲的な観測)
- シミュレーションの実行ループ（Python/RTL）と可視化ループ（Node.js）をプロセスレベルで分離し、UI の描画負荷がハードウェアの論理動作に影響を与えないようにする。
- 観測は主に共有メモリ (SHM) のポーリングを通じて行い、ターゲットの実行を停止させない。

### 2.2 Adaptive Discovery (動的適応)
- ボード構成は `board_manifest.json` を唯一の正解とし、ハードウェア構成の変更（UARTの追加、GPIOビット幅の変更等）を、サーバーの再起動なしに UI へ反映する。

### 2.3 Bridge Integration (統合された操作系)
- ログの閲覧だけでなく、UART を介した入力や、マクロによる操作自動化をサポートし、対話的なデバッグを可能にする。

## 3. 主要コンポーネント仕様

### 3.1 Dashboard Backend (`server.js`)
- **責務**: マニフェストの管理、SHM の監視、WebSocket への変換、UART ブリッジの仲介。
- **データ構造**:
    - `shmBuffer`: SHM ファイルのメモリマッピング。
    - `uartConnections`: アクティブな UART ブリッジへの TCP ソケット。
- **アルゴリズム**:
    - **Physical-to-SHM Mapping**: `physAddr - minBaseAddr` を用いて、物理アドレスから SHM 内のバイトオフセットを算出する。

### 3.2 Dashboard Frontend (React/Vue/JS)
- **詳細**: `dashboard/client/` 配下のマニフェストを参照。

## 4. 既知の未解決課題 (Known Open Issues)
- **多重接続時の競合**: 同一の UART に対して複数のブラウザタブから入力を試みた際の排他制御。
- **ヒストリカル・トレース**: レジスタ値の変化履歴（波形表示）のフロントエンドでの永続化。
