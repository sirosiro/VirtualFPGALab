#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <unistd.h>
#include <string.h>

#define I2C_DEVICE "/dev/i2c-1"
#define SLAVE_ADDR 0x50

int main() {
    printf("--- I2C Intercept Test Start ---\n");

    /* 1. Open I2C device */
    printf("[App] Opening %s...\n", I2C_DEVICE);
    int fd = open(I2C_DEVICE, O_RDWR);
    if (fd < 0) {
        perror("[App] Failed to open I2C device");
        return 1;
    }

    /* 2. Set slave address */
    printf("[App] Setting slave address to 0x%02x...\n", SLAVE_ADDR);
    if (ioctl(fd, I2C_SLAVE, SLAVE_ADDR) < 0) {
        perror("[App] Failed to set slave address");
        close(fd);
        return 1;
    }

    /* 3. Perform I2C_RDWR (Combined Write then Read) */
    printf("[App] Performing I2C_RDWR operation...\n");
    
    unsigned char write_buf[] = {0x00, 0x01}; // Register address
    unsigned char read_buf[2] = {0};

    struct i2c_msg msgs[2];
    msgs[0].addr = SLAVE_ADDR;
    msgs[0].flags = 0;
    msgs[0].len = sizeof(write_buf);
    msgs[0].buf = write_buf;

    msgs[1].addr = SLAVE_ADDR;
    msgs[1].flags = I2C_M_RD;
    msgs[1].len = sizeof(read_buf);
    msgs[1].buf = read_buf;

    struct i2c_rdwr_ioctl_data msgset;
    msgset.msgs = msgs;
    msgset.nmsgs = 2;

    if (ioctl(fd, I2C_RDWR, &msgset) < 0) {
        perror("[App] I2C_RDWR failed");
    } else {
        printf("[App] I2C_RDWR success! Read values: 0x%02x 0x%02x\n", read_buf[0], read_buf[1]);
        if (read_buf[0] == 0xAA && read_buf[1] == 0xAA) {
            printf("[App] SUCCESS: Received expected dummy values (0xAA) from Shim.\n");
        }
    }

    close(fd);
    printf("--- I2C Intercept Test End ---\n");
    return 0;
}
