#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int main() {
    printf("--- Test Open Start ---\n");

    /* Try to open a regular file */
    printf("Opening /etc/hostname...\n");
    int fd1 = open("/etc/hostname", O_RDONLY);
    if (fd1 >= 0) {
        printf("Successfully opened /etc/hostname (fd: %d)\n", fd1);
        close(fd1);
    } else {
        perror("Failed to open /etc/hostname");
    }

    /* Try to open a virtual FPGA device */
    printf("\nOpening /dev/fpga0 (Virtual Device)...\n");
    int fd2 = open("/dev/fpga0", O_RDWR);
    if (fd2 >= 0) {
        printf("Successfully opened /dev/fpga0 (fd: %d)\n", fd2);
        close(fd2);
    } else {
        /* This is expected to fail on a normal system, but our shim should log it */
        printf("Open /dev/fpga0 failed as expected (Normal behavior without full shim logic)\n");
    }

    printf("--- Test Open End ---\n");
    return 0;
}
