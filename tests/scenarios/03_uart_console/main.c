#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

int main() {
    printf("--- UART Intercept Test Start ---\n");

    printf("[App] Opening /dev/ttyPS2...\n");
    int fd = open("/dev/ttyPS2", O_RDWR | O_NOCTTY);
    if (fd < 0) {
        perror("open");
        printf("[App] FAILURE: Could not open /dev/ttyPS2\n");
        return 1;
    }

    printf("[App] Successfully opened /dev/ttyPS2 (Shim redirected it to a PTY)\n");

    const char *msg = "Hello from Virtual FPGA UART!\r\n";
    printf("[App] Sending: %s", msg);
    
    ssize_t written = write(fd, msg, strlen(msg));
    if (written < 0) {
        perror("write");
        close(fd);
        return 1;
    }

    printf("[App] Successfully wrote %zd bytes to UART\n", written);

    close(fd);
    printf("--- UART Intercept Test End ---\n");
    return 0;
}
