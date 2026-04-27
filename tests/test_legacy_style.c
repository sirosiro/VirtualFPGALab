#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <stdint.h>

// --- Mimicking sandbox/nsrc legacy style ---
#define FPGA_PHYS_ADDR 0x40000000
#define REG_SIZE 0x1000

// The "dangerously direct" macro style often found in legacy/sample code
#define WRITEL(value, address, offset) (*(volatile uint32_t *)((uint8_t *)(address) + (offset)) = (value))
#define READL(address, offset)         (*(volatile uint32_t *)((uint8_t *)(address) + (offset)))

int main() {
    printf("--- Legacy Style (sandbox-like) Test Start ---\n");

    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    // Even though they mmap, they often think in terms of the physical base
    void *virt_base = mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, FPGA_PHYS_ADDR);
    if (virt_base == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }

    printf("[App] virt_base obtained at %p\n", virt_base);

    // 1. Reset and Enable via WRITEL (Legacy style)
    printf("[App] Writing to FPGA via legacy WRITEL macro...\n");
    
    // Offset 0x10: RST, Offset 0x14: EN
    WRITEL(1, virt_base, 0x10); // Reset
    WRITEL(0, virt_base, 0x10); // Release Reset
    WRITEL(1, virt_base, 0x14); // Enable

    // 2. Read back via READL
    printf("[App] Reading counter via legacy READL macro...\n");
    uint32_t val1 = READL(virt_base, 0x18);
    printf("[App] Value 1: %u\n", val1);

    sleep(1);

    uint32_t val2 = READL(virt_base, 0x18);
    printf("[App] Value 2: %u\n", val2);

    if (val2 > val1) {
        printf("[App] SUCCESS: Legacy style macros worked on VirtualFPGALab!\n");
    } else {
        printf("[App] FAILURE: Counter did not increment (Check Shim/Sim).\n");
        return 1;
    }

    munmap(virt_base, REG_SIZE);
    close(fd);
    printf("--- Legacy Style Test End ---\n");
    return 0;
}
