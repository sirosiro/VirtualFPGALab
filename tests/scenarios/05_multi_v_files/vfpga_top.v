/* 
 * 【解説: トップモジュール vfpga_top】
 * AXI-Lite 相当のバスインターフェースを持ち、内部でサブモジュールを制御します。
 */
module vfpga_top (
    input wire clk,          // クロック
    input wire rst_n,        // リセット（負論理）
    input wire [31:0] addr,  // アドレス
    input wire [31:0] w_data, // 書き込みデータ
    input wire w_en,         // 書き込み有効信号
    output wire [31:0] r_data // 読み出しデータ
);
    reg [31:0] reg0;
    wire [31:0] sub_out;

    /* 
     * 【解説: サブモジュールのインスタンス化】
     * 別のファイル (sub_logic.v) で定義されたモジュールを呼び出します。
     * REG0 の値と、現在の書き込みデータを入力として渡します。
     */
    sub_logic u_sub (
        .in_a(reg0),
        .in_b(w_data),
        .out_y(sub_out)
    );

    /* 【解説: レジスタ書き込みロジック】 */
    always @(posedge clk) begin
        if (!rst_n) begin
            reg0 <= 32'h0;
        end else if (w_en && addr == 32'h0) begin
            reg0 <= w_data;
        end
    end

    /* 
     * 【解説: 読み出しロジック】
     * アドレス 0x4 (REG1) を読み出した際に、サブモジュールの結果を返します。
     */
    assign r_data = (addr == 32'h4) ? sub_out : reg0;

endmodule
