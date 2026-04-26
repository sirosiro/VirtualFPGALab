
#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>
#include <stdarg.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <sys/ioctl.h>

#define SHM_NAME "/vfpga_reg"
#define MAX_FDS 1024
static int is_virtual_fd[MAX_FDS] = {0};

static int (*original_open)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*original_ioctl)(int fd, unsigned long request, void *argp) = NULL;

static int get_device_type(const char *pathname) {
    if (pathname != NULL && strcmp(pathname, "/dev/vfpga_reg") == 0) return 1;
    if (pathname != NULL && strcmp(pathname, "/dev/fpga0") == 0) return 1;
    if (pathname != NULL && strcmp(pathname, "/dev/i2c-1") == 0) return 2;
    return 0;
}

int open(const char *pathname, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list arg;
        va_start(arg, flags);
        mode = va_arg(arg, mode_t);
        va_end(arg);
    }

    if (!original_open) original_open = dlsym(RTLD_NEXT, "open");

    int type = get_device_type(pathname);

    if (type == 1) {
        fprintf(stderr, "[Shim] Intercepting FPGA/UIO access: %s\n", pathname);
        fflush(stderr);
        int fd = shm_open(SHM_NAME, flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 1;
        return fd;
    }

    if (type == 2) {
        fprintf(stderr, "[Shim] Intercepting I2C access: %s\n", pathname);
        fflush(stderr);
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 2;
        return fd;
    }

    return original_open(pathname, flags, mode);
}

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
                if (data->msgs[i].flags & I2C_M_RD) {
                    memset(data->msgs[i].buf, 0xAA, data->msgs[i].len);
                }
            }
            fflush(stderr);
            return 0;
        }
        if (request == I2C_SLAVE || request == I2C_SLAVE_FORCE) {
            return 0;
        }
    }

    return original_ioctl(fd, request, argp);
}
