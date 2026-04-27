/* Standard RTL for VirtualFPGALab Tests */
module vfpga_top (
    input wire clk,
    input wire rst_n,
    input wire [31:0] addr,
    input wire [31:0] w_data,
    input wire w_en,
    output reg [31:0] r_data,
    
    // Register Ports (Managed by Simulator/DTS)
    output reg [31:0] RST,
    output reg [31:0] EN,
    output reg [31:0] CNT
);

    // Write Logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            RST <= 32'h0;
            EN  <= 32'h0;
        end else if (w_en) begin
            case (addr)
                32'h10: RST <= w_data;
                32'h14: EN  <= w_data;
                default: ;
            endcase
        end
    end

    // Read Logic
    always @(*) begin
        case (addr)
            32'h10: r_data = RST;
            32'h14: r_data = EN;
            32'h18: r_data = CNT;
            default: r_data = 32'hdeadbeef;
        endcase
    end

    // Counter Logic (The "Functional" part sirosiro is studying)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n || RST[0]) begin
            CNT <= 32'h0;
        end else if (EN[0]) begin
            CNT <= CNT + 1;
        end
    end

endmodule
