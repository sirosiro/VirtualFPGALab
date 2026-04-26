#!/usr/bin/env python3
import re
import os
import sys

def parse_dts(dts_path):
    with open(dts_path, 'r') as f:
        content = f.read()

    # Simple regex to find nodes and their properties
    # This is a very basic parser for demonstration
    nodes = []
    # Find patterns like node@addr { ... }
    matches = re.finditer(r'([a-zA-Z0-9_@]+)\s*\{([^}]+)\}', content)
    for match in matches:
        name = match.group(1).strip()
        body = match.group(2)
        
        props = {}
        # Find patterns like key = <val>; or key = "val";
        prop_matches = re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*([^;]+);', body)
        for p_match in prop_matches:
            k = p_match.group(1).strip()
            v = p_match.group(2).strip()
            # Clean up values
            if v.startswith('<') and v.endswith('>'):
                v = v[1:-1].strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1].strip()
            props[k] = v
        
        if 'label' in props:
            nodes.append({
                'name': name,
                'path': props['label'],
                'type': 'uio' if 'generic-uio' in props.get('compatible', '') else 'i2c',
                'reg': props.get('reg', '0x0 0x0'),
                'bus_id': props.get('bus_id', '0')
            })
    return nodes

def generate_c_code(nodes):
    uio_matches = []
    i2c_matches = []
    
    for node in nodes:
        if node['type'] == 'uio':
            uio_matches.append(f'    if (pathname != NULL && strcmp(pathname, "{node["path"]}") == 0) return 1;')
        else:
            i2c_matches.append(f'    if (pathname != NULL && strcmp(pathname, "{node["path"]}") == 0) return 2;')

    template = f"""
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
static int is_virtual_fd[MAX_FDS] = {{0}};

static int (*original_open)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*original_ioctl)(int fd, unsigned long request, void *argp) = NULL;

static int get_device_type(const char *pathname) {{
{chr(10).join(uio_matches)}
{chr(10).join(i2c_matches)}
    return 0;
}}

int open(const char *pathname, int flags, ...) {{
    mode_t mode = 0;
    if (flags & O_CREAT) {{
        va_list arg;
        va_start(arg, flags);
        mode = va_arg(arg, mode_t);
        va_end(arg);
    }}

    if (!original_open) original_open = dlsym(RTLD_NEXT, "open");

    int type = get_device_type(pathname);

    if (type == 1) {{
        fprintf(stderr, "[Shim] Intercepting FPGA/UIO access: %s\\n", pathname);
        fflush(stderr);
        int fd = shm_open(SHM_NAME, flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 1;
        return fd;
    }}

    if (type == 2) {{
        fprintf(stderr, "[Shim] Intercepting I2C access: %s\\n", pathname);
        fflush(stderr);
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 2;
        return fd;
    }}

    return original_open(pathname, flags, mode);
}}

int ioctl(int fd, unsigned long request, ...) {{
    va_list args;
    va_start(args, request);
    void *argp = va_arg(args, void *);
    va_end(args);

    if (!original_ioctl) original_ioctl = dlsym(RTLD_NEXT, "ioctl");

    if (fd >= 0 && fd < MAX_FDS && is_virtual_fd[fd] == 2) {{
        if (request == I2C_RDWR) {{
            struct i2c_rdwr_ioctl_data *data = (struct i2c_rdwr_ioctl_data *)argp;
            fprintf(stderr, "[Shim] Intercepted I2C_RDWR: %u messages\\n", data->nmsgs);
            for (unsigned int i = 0; i < data->nmsgs; i++) {{
                if (data->msgs[i].flags & I2C_M_RD) {{
                    memset(data->msgs[i].buf, 0xAA, data->msgs[i].len);
                }}
            }}
            fflush(stderr);
            return 0;
        }}
        if (request == I2C_SLAVE || request == I2C_SLAVE_FORCE) {{
            return 0;
        }}
    }}

    return original_ioctl(fd, request, argp);
}}
"""
    return template

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: gen_shim.py <dts_path> <output_c_path>")
        sys.exit(1)
    
    dts_path = sys.argv[1]
    output_path = sys.argv[2]
    
    nodes = parse_dts(dts_path)
    c_code = generate_c_code(nodes)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(c_code)
    print(f"Generated {output_path} from {dts_path}")
