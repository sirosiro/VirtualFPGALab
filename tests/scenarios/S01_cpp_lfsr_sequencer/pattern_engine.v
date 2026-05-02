/* Custom Pattern Engine with LFSR and Sequencer */
module pattern_engine (
    input  wire        clk,
    input  wire        rst_n,
    /* verilator lint_off UNUSED */
    input  wire [31:0] ctrl,      // [0]=RUN, [2:1]=MODE
    /* verilator lint_on UNUSED */
    input  wire [31:0] speed,     // Tick interval
    output reg  [31:0] status     // Current LED pattern
);

    reg [31:0] tick_counter;
    reg        tick;
    reg [15:0] lfsr_reg;
    reg [7:0]  bin_counter;
    reg [7:0]  seq_reg;

    wire run  = ctrl[0];
    wire [1:0] mode = ctrl[2:1];

    // 1. Clock Divider
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tick_counter <= 0;
            tick <= 0;
        end else if (run) begin
            if (tick_counter >= speed) begin
                tick_counter <= 0;
                tick <= 1;
            end else begin
                tick_counter <= tick_counter + 1;
                tick <= 0;
            end
        end else begin
            tick <= 0;
        end
    end

    // 2. LFSR (Pseudo Random Generator)
    // Polynomial: x^16 + x^14 + x^13 + x^11 + 1
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lfsr_reg <= 16'hACE1; // Seed
        end else if (tick && mode == 2'd2) begin
            lfsr_reg <= {lfsr_reg[14:0], lfsr_reg[15] ^ lfsr_reg[13] ^ lfsr_reg[12] ^ lfsr_reg[10]};
        end
    end

    // 3. Binary Counter
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bin_counter <= 0;
        end else if (tick && mode == 2'd1) begin
            bin_counter <= bin_counter + 1;
        end
    end

    // 4. Sequential (Chaser)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seq_reg <= 8'h01;
        end else if (tick && mode == 2'd0) begin
            seq_reg <= {seq_reg[6:0], seq_reg[7]};
        end
    end

    // 5. Output Multiplexer
    always @(*) begin
        case (mode)
            2'd0:    status = {24'h0, seq_reg};
            2'd1:    status = {24'h0, bin_counter};
            2'd2:    status = {16'h0, lfsr_reg};
            default: status = 32'h0;
        endcase
    end

endmodule
