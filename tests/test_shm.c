#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdint.h>

#define SHM_NAME "/vfpga_reg"
#define SHM_SIZE 1024

int main() {
    printf("--- Test Shared Memory Start ---\n");

    /* Open shared memory */
    int fd = shm_open(SHM_NAME, O_RDONLY, 0666);
    if (fd == -1) {
        perror("shm_open failed. Is the Python controller running?");
        return 1;
    }

    /* Map shared memory */
    uint32_t *ptr = mmap(NULL, SHM_SIZE, PROT_READ, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) {
        perror("mmap failed");
        close(fd);
        return 1;
    }

    /* Read value from offset 0 */
    uint32_t val = ptr[0];
    printf("[C] Read value from shared memory: 0x%08X\n", val);

    if (val == 0x12345678) {
        printf("[C] SUCCESS: Value matches expected 0x12345678\n");
    } else {
        printf("[C] FAILURE: Value 0x%08X does not match expected 0x12345678\n", val);
    }

    /* Cleanup */
    munmap(ptr, SHM_SIZE);
    close(fd);

    printf("--- Test Shared Memory End ---\n");
    return 0;
}
