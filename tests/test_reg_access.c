#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>

#define VIRTUAL_DEVICE "/dev/fpga0"
#define REG_SIZE 1024

int main() {
    printf("--- Register Access Test Start ---\n");

    /* 1. Open virtual device (will be intercepted by shim) */
    printf("[App] Opening %s...\n", VIRTUAL_DEVICE);
    int fd = open(VIRTUAL_DEVICE, O_RDWR);
    if (fd == -1) {
        perror("[App] Failed to open virtual device. Is the Python controller running?");
        return 1;
    }

    /* 2. Mmap the device memory */
    printf("[App] Mapping device memory...\n");
    uint32_t *regs = mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (regs == MAP_FAILED) {
        perror("[App] mmap failed");
        close(fd);
        return 1;
    }

    /* 3. Read initial value (set by Python) */
    printf("[App] Reading register at offset 0x00...\n");
    uint32_t val = regs[0];
    printf("[App] Value: 0x%08X\n", val);

    if (val == 0x12345678) {
        printf("[App] SUCCESS: Correct initial value read from virtual device!\n");
    } else {
        printf("[App] FAILURE: Unexpected value 0x%08X\n", val);
    }

    /* 4. Write a value to register at offset 0x04 */
    uint32_t write_val = 0xCAFEBABE;
    printf("[App] Writing 0x%08X to offset 0x04...\n", write_val);
    regs[1] = write_val;

    /* Cleanup */
    munmap(regs, REG_SIZE);
    close(fd);

    printf("--- Register Access Test End ---\n");
    return 0;
}
