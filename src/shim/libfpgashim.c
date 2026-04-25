#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>
#include <stdarg.h>
#include <fcntl.h>

#include <sys/mman.h>
#include <sys/stat.h>

#define SHM_NAME "/vfpga_reg"

#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <sys/ioctl.h>

#define MAX_FDS 1024
static int is_virtual_fd[MAX_FDS] = {0};

/* Original function pointers */
static int (*original_open)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*original_ioctl)(int fd, unsigned long request, void *argp) = NULL;

/* 
 * Hooked open function
 */
int open(const char *pathname, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list arg;
        va_start(arg, flags);
        mode = va_arg(arg, mode_t);
        va_end(arg);
    }

    if (!original_open) original_open = dlsym(RTLD_NEXT, "open");

    int is_fpga = (pathname != NULL && (strncmp(pathname, "/dev/fpga", 9) == 0 || strncmp(pathname, "/dev/uio", 8) == 0));
    int is_i2c = (pathname != NULL && strncmp(pathname, "/dev/i2c-", 9) == 0);

    if (is_fpga) {
        fprintf(stderr, "[Shim] Intercepting FPGA access: %s\n", pathname);
        fflush(stderr);
        int fd = shm_open(SHM_NAME, flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 1;
        return fd;
    }

    if (is_i2c) {
        fprintf(stderr, "[Shim] Intercepting I2C access: %s\n", pathname);
        fflush(stderr);
        /* For I2C, we might return a dummy FD or the real one if we want to mix.
           For now, let's use a dummy /dev/null FD to simulate a handle. */
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 2; // 2 means I2C
        return fd;
    }

    return original_open(pathname, flags, mode);
}

/*
 * Hooked ioctl function
 */
int ioctl(int fd, unsigned long request, ...) {
    va_list args;
    va_start(args, request);
    void *argp = va_arg(args, void *);
    va_end(args);

    if (!original_ioctl) original_ioctl = dlsym(RTLD_NEXT, "ioctl");

    if (fd >= 0 && fd < MAX_FDS && is_virtual_fd[fd] == 2) {
        if (request == I2C_RDWR) {
            struct i2c_rdwr_ioctl_data *data = (struct i2c_rdwr_ioctl_data *)argp;
            fprintf(stderr, "[Shim] Intercepted I2C_RDWR: %u messages\n", data->nmsgs);
            for (unsigned int i = 0; i < data->nmsgs; i++) {
                fprintf(stderr, "[Shim]  Msg[%d]: Addr=0x%02x, Flags=0x%04x, Len=%d\n", 
                        i, data->msgs[i].addr, data->msgs[i].flags, data->msgs[i].len);
                /* Here we would interact with Python/SHM to get/set data */
                if (data->msgs[i].flags & I2C_M_RD) {
                    memset(data->msgs[i].buf, 0xAA, data->msgs[i].len); // Dummy read data
                }
            }
            fflush(stderr);
            return 0; // Success
        }
        if (request == I2C_SLAVE || request == I2C_SLAVE_FORCE) {
            fprintf(stderr, "[Shim] Intercepted I2C_SLAVE: Addr=0x%02lx\n", (unsigned long)argp);
            fflush(stderr);
            return 0;
        }
    }

    return original_ioctl(fd, request, argp);
}
