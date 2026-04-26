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

    // Write and Read back test via Shim
    uint32_t test_val = 0x55AA55AA;
    printf("[App] Writing 0x%08X to virtual register offset 0x00...\n", test_val);
    regs[0] = test_val;

    printf("[App] Reading register at offset 0x00...\n");
    uint32_t val = regs[0];
    printf("[App] Value: 0x%08X\n", val);

    if (val == test_val) {
        printf("[App] SUCCESS: Write/Read back via Shim verified!\n");
    } else {
        printf("[App] FAILURE: Value mismatch!\n");
    }

    munmap(regs, REG_SIZE);
    close(fd);

    printf("--- Register Access Test End ---\n");
    return 0;
}
