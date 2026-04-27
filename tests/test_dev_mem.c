#include <stdio.h>
#include <stdint.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>

#define DEV_MEM "/dev/mem"
#define FPGA_REG_BASE 0x40000000
#define REG_SIZE 0x1000

int main() {
    printf("--- /dev/mem Intercept Test Start ---\n");

    // 1. Open /dev/mem
    printf("[App] Opening %s...\n", DEV_MEM);
    int fd = open(DEV_MEM, O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    // 2. Map physical address 0x40000000
    printf("[App] Mapping physical address 0x%08X...\n", FPGA_REG_BASE);
    uint32_t *regs = (uint32_t *)mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, FPGA_REG_BASE);
    if (regs == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }

    // 3. Enable Counter (Offset 0x14 is the Enable register)
    printf("[App] Enabling counter via offset 0x14...\n");
    regs[0x14/4] = 1;

    // 4. Access register (Offset 0x18 is the Counter in our vfpga_top)
    printf("[App] Reading counter at offset 0x18...\n");
    uint32_t val1 = regs[0x18/4];
    printf("[App] Counter value 1: %u\n", val1);

    sleep(1);

    uint32_t val2 = regs[0x18/4];
    printf("[App] Counter value 2: %u\n", val2);

    if (val2 > val1) {
        printf("[App] SUCCESS: Counter incremented via /dev/mem mapping!\n");
    } else {
        printf("[App] FAILURE: Counter did not increment (Val1: %u, Val2: %u).\n", val1, val2);
    }

    munmap(regs, REG_SIZE);
    close(fd);
    printf("--- /dev/mem Intercept Test End ---\n");

    return 0;
}
