#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <string.h>

int read_from_bus(const char* path, unsigned char slave_addr) {
    int fd = open(path, O_RDWR);
    if (fd < 0) {
        perror("open");
        return -1;
    }

    unsigned char buf[1] = {0};
    struct i2c_msg msgs[1];
    struct i2c_rdwr_ioctl_data msgset[1];

    msgs[0].addr = slave_addr;
    msgs[0].flags = I2C_M_RD;
    msgs[0].len = 1;
    msgs[0].buf = buf;

    msgset[0].msgs = msgs;
    msgset[0].nmsgs = 1;

    if (ioctl(fd, I2C_RDWR, &msgset) < 0) {
        perror("ioctl");
        close(fd);
        return -1;
    }

    close(fd);
    return buf[0];
}

int main() {
    printf("--- Multi-I2C Test Start ---\n");

    int val1 = read_from_bus("/dev/i2c-1", 0x50);
    printf("[App] Bus 1 (0x50) returned: 0x%02X\n", val1);

    int val2 = read_from_bus("/dev/i2c-2", 0x36);
    printf("[App] Bus 2 (0x36) returned: 0x%02X\n", val2);

    if (val1 == 0x10 && val2 == 0x20) {
        printf("[App] SUCCESS: Multiple I2C buses identified correctly!\n");
    } else {
        printf("[App] FAILURE: Unexpected data (Expected 0x10 and 0x20)\n");
    }

    printf("--- Multi-I2C Test End ---\n");
    return 0;
}
