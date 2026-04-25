#include <iostream>
#include <verilated.h>
#include "Vcounter.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>

#define SHM_NAME "/vfpga_reg"
#define SHM_SIZE 1024

// Register Offsets
#define REG_RST    (0x10 / 4)
#define REG_EN     (0x14 / 4)
#define REG_COUNT  (0x18 / 4)

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vcounter* top = new Vcounter;

    // Attach to shared memory
    int fd = shm_open(SHM_NAME, O_RDWR, 0666);
    if (fd == -1) {
        std::cerr << "[Sim] shm_open failed. Please run vlogic_controller.py first." << std::endl;
        return 1;
    }

    uint32_t* regs = (uint32_t*)mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (regs == MAP_FAILED) {
        perror("[Sim] mmap failed");
        return 1;
    }

    std::cout << "[Sim] Verilator simulation started. Syncing with SHM..." << std::endl;

    // Initial state
    top->clk = 0;
    top->rst = 1;
    top->en = 0;

    uint64_t main_time = 0;
    while (!Verilated::gotFinish()) {
        // Sync inputs from SHM to RTL
        top->rst = regs[REG_RST] & 0x1;
        top->en  = regs[REG_EN]  & 0x1;

        // Toggle clock
        top->clk = !top->clk;
        top->eval();

        // Sync outputs from RTL to SHM
        if (top->clk) {
            regs[REG_COUNT] = top->count;
        }

        main_time++;
        
        // Slow down simulation to avoid 100% CPU usage
        usleep(10000); // 10ms per half-clock
    }

    top->final();
    delete top;
    return 0;
}
