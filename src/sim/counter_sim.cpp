#include <iostream>
#include <verilated.h>
#include "Vvfpga_top.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>

#include "vfpga_config.h"

// These offsets should ideally come from a shared header or DTS
#define ADDR_RST    0x10
#define ADDR_EN     0x14
#define ADDR_COUNT  0x18

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vvfpga_top* top = new Vvfpga_top;

    int fd = shm_open(SHM_NAME, O_RDWR, 0666);
    if (fd == -1) {
        std::cerr << "[Sim] shm_open failed. Run vlogic_controller.py first." << std::endl;
        return 1;
    }

    uint8_t* shm_ptr = (uint8_t*)mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (shm_ptr == MAP_FAILED) {
        perror("[Sim] mmap failed");
        return 1;
    }

    std::cout << "[Sim] Verilator simulation (vfpga_top) started." << std::endl;

    top->clk = 0;
    top->rst_n = 1;

    while (!Verilated::gotFinish()) {
        // Sync inputs from SHM to RTL
        top->addr = 0; // Not used in this simple sync, but could be
        top->w_en = 0;

        // In this generic sync, we map SHM offsets directly to RTL registers
        // This is a bit manual, but demonstrates the link
        top->RST = *(uint32_t*)(shm_ptr + ADDR_RST);
        top->EN  = *(uint32_t*)(shm_ptr + ADDR_EN);

        // Toggle clock
        top->clk = !top->clk;
        top->rst_n = 1; // Always active high reset in this mock
        top->eval();

        // Sync outputs from RTL back to SHM
        if (top->clk) {
            *(uint32_t*)(shm_ptr + ADDR_COUNT) = top->CNT;
        }

        usleep(10000); 
    }

    top->final();
    delete top;
    return 0;
}
