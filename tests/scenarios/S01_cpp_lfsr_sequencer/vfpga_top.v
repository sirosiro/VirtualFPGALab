/* Top-level module: Integrated Bus & Custom IP */
module vfpga_top (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] addr,
    input  wire [31:0] w_data,
    input  wire        w_en,
    output reg  [31:0] r_data,
    // GPIO Registers
    output reg  [31:0] DATA,
    output reg  [31:0] TRI,
    // Custom Engine Registers
    output reg  [31:0] CTRL,
    output reg  [31:0] SPEED,
    output reg  [31:0] STATUS
);

    wire [31:0] engine_out;
    
    // Instantiate Custom Pattern Engine
    pattern_engine u_engine (
        .clk    (clk),
        .rst_n  (rst_n),
        .ctrl   (CTRL),
        .speed  (SPEED),
        .status (engine_out)
    );

    // Register Write Logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            DATA   <= 32'h0;
            TRI    <= 32'hFFFFFFFF;
            CTRL   <= 32'h0;
            SPEED  <= 32'h01000000; // Default slow speed
        end else if (w_en) begin
            case (addr)
                // GPIO Address Space
                32'h41200000: DATA <= w_data;
                32'h41200004: TRI  <= w_data;
                // Custom Engine Address Space
                32'h42000000: CTRL <= w_data;
                32'h42000004: SPEED <= w_data;
                default: ;
            endcase
        end
    end

    // Register Read Logic & Data Routing
    always @(*) begin
        // Update STATUS register with actual engine output
        STATUS = engine_out;
        
        case (addr)
            32'h41200000: r_data = (CTRL[0]) ? engine_out : DATA; // Mix: HW or SW
            32'h41200004: r_data = TRI;
            32'h42000000: r_data = CTRL;
            32'h42000004: r_data = SPEED;
            32'h42000008: r_data = engine_out;
            default:      r_data = 32'hDEADBEEF;
        endcase
    end

endmodule
