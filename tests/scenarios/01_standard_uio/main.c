#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>

#define VIRTUAL_DEVICE "/dev/fpga0"
#define REG_SIZE 1024

int main() {
    printf("--- Standard UIO and Verilator Sync Test Start ---\n");

    printf("[App] Opening %s...\n", VIRTUAL_DEVICE);
    int fd = open(VIRTUAL_DEVICE, O_RDWR);
    if (fd == -1) {
        perror("open failed");
        return 1;
    }

    printf("[App] Mapping device memory...\n");
    uint32_t *regs = mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (regs == MAP_FAILED) {
        perror("mmap failed");
        close(fd);
        return 1;
    }

    // Part 1: Basic Read/Write
    regs[0] = 0x12345678;
    if (regs[0] == 0x12345678) {
        printf("[App] SUCCESS: Basic register R/W verified.\n");
    }

    // Part 2: Verilator logic synchronization (Counter)
    printf("[App] Resetting counter via offset 0x10...\n");
    regs[4] = 1; // 0x10 / 4 = 4
    regs[4] = 0;

    printf("[App] Enabling counter via offset 0x14...\n");
    regs[5] = 1; // 0x14 / 4 = 5

    printf("[App] Waiting for counter to increment (handled by Verilator)...\n");
    sleep(1);
    uint32_t val1 = regs[6]; // 0x18 / 4 = 6
    sleep(1);
    uint32_t val2 = regs[6];

    printf("[App] Counter value 1: %u, Value 2: %u\n", val1, val2);
    if (val2 > val1) {
        printf("[App] SUCCESS: Verilator logic (counter) is running and synced!\n");
    } else {
        printf("[App] FAILURE: Counter is not moving. Check RTL/Simulator.\n");
        return 1;
    }

    munmap(regs, REG_SIZE);
    close(fd);
    return 0;
}
