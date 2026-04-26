#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>

/* アプリは標準的なデバイスパスしか知らない */
#define VIRTUAL_DEVICE "/dev/fpga0"
#define REG_SIZE 1024

int main() {
    printf("--- Test Application Access (via Shim) Start ---\n");

    /* 1. 標準的な open() を呼び出す。Shimがこれをインターセプトする */
    printf("[App] Opening %s...\n", VIRTUAL_DEVICE);
    int fd = open(VIRTUAL_DEVICE, O_RDWR);
    if (fd == -1) {
        perror("[App] open failed. Is the Shim loaded correctly?");
        return 1;
    }

    /* 2. mmap() も標準的な方法で行う */
    uint32_t *ptr = mmap(NULL, REG_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) {
        perror("[App] mmap failed");
        close(fd);
        return 1;
    }

    /* 3. 書き込みと読み出しの検証 */
    uint32_t test_val = 0xDEADBEEF;
    printf("[App] Writing 0x%08X to virtual device...\n", test_val);
    ptr[0] = test_val;

    uint32_t val = ptr[0];
    printf("[App] Read back value: 0x%08X\n", val);

    if (val == test_val) {
        printf("[App] SUCCESS: Hardware Transparency Verified!\n");
    } else {
        printf("[App] FAILURE: Value mismatch!\n");
    }

    /* Cleanup */
    munmap(ptr, REG_SIZE);
    close(fd);

    printf("--- Test Application Access End ---\n");
    return 0;
}
