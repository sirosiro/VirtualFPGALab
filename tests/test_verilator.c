#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>

#define VIRTUAL_DEVICE "/dev/fpga0"
#define REG_SIZE 1024

// Register Offsets
#define REG_RST    (0x10 / 4)
#define REG_EN     (0x14 / 4)
#define REG_COUNT  (0x18 / 4)

int main() {
    printf("--- Verilator RTL Test Start ---\n");

    int fd = open(VIRTUAL_DEVICE, O_RDWR);
    if (fd == -1) {
        perror("open failed");
        return 1;
    }

    uint32_t *regs = mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (regs == MAP_FAILED) {
        perror("mmap failed");
        return 1;
    }

    // 1. Reset Release
    printf("[App] Releasing Reset...\n");
    regs[REG_RST] = 0;
    
    // 2. Enable Counter
    printf("[App] Enabling Counter...\n");
    regs[REG_EN] = 1;

    // 3. Wait and read count
    printf("[App] Waiting for counter to increment...\n");
    for (int i = 0; i < 5; i++) {
        sleep(1);
        printf("[App] Counter value: %u\n", regs[REG_COUNT]);
    }

    // 4. Disable Counter
    printf("[App] Disabling Counter...\n");
    regs[REG_EN] = 0;
    uint32_t last_val = regs[REG_COUNT];
    sleep(1);
    printf("[App] Counter value after 1s: %u (Should be same as %u)\n", regs[REG_COUNT], last_val);

    munmap(regs, REG_SIZE);
    close(fd);

    printf("--- Verilator RTL Test End ---\n");
    return 0;
}
