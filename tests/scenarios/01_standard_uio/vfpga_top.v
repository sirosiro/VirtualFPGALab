/*
 * 【解説: VerilogとDTSの関係（実機開発との違い）】
 * 初学者の皆さんへ：今見ているこのファイル (`vfpga_top.v`) がFPGAの「ハードウェア回路」の記述です。
 * 
 * 実際のFPGA開発（Xilinx Vivado等）では、まずこのようなVerilogコード（回路）を書き、
 * その回路の構成をツールが読み取って `.dts` を自動生成します。
 * 
 * しかし F-BB では、学習やエミュレーションの都合上、アプローチを逆にしています。
 * まず `config.dts` に「欲しいレジスタ」を書き、それに合わせて
 * この `vfpga_top.v` の外枠（module宣言やポート、バスの配線）を用意する形になります。
 */
module vfpga_top (
    input wire clk,
    input wire rst_n,
    input wire [31:0] addr,
    input wire [31:0] w_data,
    input wire w_en,
    output reg [31:0] r_data
);

    // 内部レジスタ
    reg [31:0] RST;
    reg [31:0] EN;
    reg [31:0] CNT;

    // 【解説: レジスタへの書き込み処理】
    // ソフトウェア(C言語)から書き込み要求 (w_en = 1) が来た際に、
    // アドレス (addr) を見て、対象のレジスタにデータ (w_data) を保存します。
    // ※ ここは config.dts の定義に従って記述する、バスインターフェースの定型処理部分です。
    // Write Logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            RST <= 32'h0;
            EN  <= 32'h0;
        end else if (w_en) begin
            case (addr)
                32'h40000010: RST <= w_data;
                32'h40000014: EN  <= w_data;
                default: ;
            endcase
        end
    end

    // 【解説: レジスタからの読み出し処理】
    // ソフトウェアから読み出し要求が来た際に、アドレス (addr) に応じて
    // 該当するレジスタの値を r_data に返してC言語側に伝達します。
    // Read Logic
    always @(*) begin
        case (addr)
            32'h40000010: r_data = RST;
            32'h40000014: r_data = EN;
            32'h40000018: r_data = CNT;
            default: r_data = 32'hdeadbeef;
        endcase
    end

    // 【解説: ユーザー独自の実装部分 (カウンター回路)】
    // ここから下が、学習者が実装するメインのハードウェアロジックです。
    // ENレジスタの最下位ビット (EN[0]) が1の間、クロック(clk)の立ち上がりに合わせてCNTをカウントアップします。
    // Counter Logic (The "Functional" part sirosiro is studying)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n || RST[0]) begin
            CNT <= 32'h0;
        end else if (EN[0]) begin
            CNT <= CNT + 1;
        end
    end

endmodule
