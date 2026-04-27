#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>

#define VIRTUAL_DEVICE "/dev/mem"
#define FPGA_BASE_ADDR 0x40000000
#define REG_SIZE 1024

// Macros from common FPGA samples
#define WRITEL(val, base, offset) (*(volatile uint32_t *)((uintptr_t)base + offset) = val)
#define READL(base, offset)       (*(volatile uint32_t *)((uintptr_t)base + offset))

int main() {
    printf("--- /dev/mem and Legacy Style Test Start ---\n");

    int fd = open(VIRTUAL_DEVICE, O_RDWR | O_SYNC);
    if (fd == -1) {
        perror("open /dev/mem failed");
        return 1;
    }

    printf("[App] Mapping physical address 0x%08X via /dev/mem...\n", FPGA_BASE_ADDR);
    void *virt_base = mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, FPGA_BASE_ADDR);
    if (virt_base == MAP_FAILED) {
        perror("mmap failed");
        close(fd);
        return 1;
    }

    // Part 1: Direct pointer access
    uint32_t *regs = (uint32_t *)virt_base;
    printf("[App] Writing 0x1 to EN (offset 0x14)...\n");
    regs[5] = 1; // 0x14 / 4 = 5

    sleep(1);
    uint32_t cnt = regs[6]; // 0x18 / 4 = 6
    printf("[App] Counter value: %u\n", cnt);
    if (cnt > 0) {
        printf("[App] SUCCESS: /dev/mem direct access works!\n");
    }

    // Part 2: Legacy Macro access
    printf("[App] Testing via legacy WRITEL/READL macros...\n");
    WRITEL(1, virt_base, 0x10); // Reset
    WRITEL(0, virt_base, 0x10);
    
    WRITEL(1, virt_base, 0x14); // Enable
    sleep(1);
    uint32_t val1 = READL(virt_base, 0x18);
    sleep(1);
    uint32_t val2 = READL(virt_base, 0x18);
    
    printf("[App] Value 1: %u, Value 2: %u\n", val1, val2);
    if (val2 > val1) {
        printf("[App] SUCCESS: Legacy macros verified!\n");
    } else {
        printf("[App] FAILURE: Counter not incrementing!\n");
        return 1;
    }

    munmap(virt_base, REG_SIZE);
    close(fd);
    return 0;
}
