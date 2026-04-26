#!/usr/bin/env python3
import re
import os
import sys

def parse_dts(dts_path):
    with open(dts_path, 'r') as f:
        content = f.read()

    nodes = []
    # Find patterns like node@addr { ... }
    matches = re.finditer(r'([a-zA-Z0-9_@]+)\s*\{([^}]+)\}', content)
    for match in matches:
        raw_name = match.group(1).strip()
        name = raw_name.split('@')[0] # Get 'vfpga_reg' from 'vfpga_reg@40000000'
        body = match.group(2)
        
        props = {}
        prop_matches = re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*([^;]+);', body)
        for p_match in prop_matches:
            k = p_match.group(1).strip()
            v = p_match.group(2).strip()
            if v.startswith('<') and v.endswith('>'):
                v = v[1:-1].strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1].strip()
            props[k] = v
        
        if 'label' in props:
            node = {
                'name': name,
                'path': props['label'],
                'type': 'uio' if 'generic-uio' in props.get('compatible', '') else 'i2c',
                'reg': props.get('reg', '0x0 0x0'),
                'registers': []
            }
            if 'registers' in props:
                reg_list = props['registers'].split(',')
                for r in reg_list:
                    r = r.strip().strip('"')
                    if '@' in r:
                        reg_name, reg_offset = r.split('@')
                        node['registers'].append({
                            'name': reg_name.strip(),
                            'offset': reg_offset.strip()
                        })
            nodes.append(node)
    return nodes

def generate_config_h(nodes):
    uio_node = next((n for n in nodes if n['type'] == 'uio'), None)
    shm_name = f"/{uio_node['name']}" if uio_node else "/vfpga_reg"
    
    template = f"""/* Auto-generated Config from DTS */
#ifndef VFPGA_CONFIG_H
#define VFPGA_CONFIG_H

#define SHM_NAME "{shm_name}"
#define SHM_SIZE 1024

#endif
"""
    return template

def generate_shim_c(nodes):
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
#include "vfpga_config.h"

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
        int fd = shm_open(SHM_NAME, flags, mode);
        if (fd != -1 && fd < MAX_FDS) is_virtual_fd[fd] = 1;
        return fd;
    }}
    if (type == 2) {{
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
            for (unsigned int i = 0; i < data->nmsgs; i++) {{
                if (data->msgs[i].flags & I2C_M_RD) {{
                    memset(data->msgs[i].buf, 0xAA, data->msgs[i].len);
                }}
            }}
            return 0;
        }}
        if (request == I2C_SLAVE || request == I2C_SLAVE_FORCE) return 0;
    }}
    return original_ioctl(fd, request, argp);
}}
"""
    return template

def generate_rtl_v(nodes):
    target_node = next((n for n in nodes if n['type'] == 'uio' and n['registers']), None)
    if not target_node:
        return ""

    reg_port_list = []
    for reg in target_node['registers']:
        reg_port_list.append(f"    output reg [31:0] {reg['name']}")
    reg_ports = ",\n".join(reg_port_list)

    template = f"""
/* Auto-generated RTL Skeleton from DTS */
module vfpga_top (
    input wire clk,
    input wire rst_n,
    input wire [31:0] addr,
    input wire [31:0] w_data,
    input wire w_en,
    output reg [31:0] r_data,
    
    // Register Ports
    {reg_ports}
);

    // Write Logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
"""
    for reg in target_node['registers']:
        template += f"            {reg['name']} <= 32'h0;\n"
    
    template += """        end else if (w_en) begin
            case (addr)
"""
    for reg in target_node['registers']:
        if reg['name'] in ['RST', 'EN']:
            v_offset = reg['offset'].replace('0x', "32'h")
            template += f"                {v_offset}: {reg['name']} <= w_data;\n"
    
    template += """                default: ;
            endcase
        end
    end

    // Read Logic
    always @(*) begin
        case (addr)
"""
    for reg in target_node['registers']:
        v_offset = reg['offset'].replace('0x', "32'h")
        template += f"            {v_offset}: r_data = {reg['name']};\n"
    
    template += """            default: r_data = 32'hdeadbeef;
        endcase
    end

    // Example Logic: Counter
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n || RST[0]) begin
            CNT <= 32'h0;
        end else if (EN[0]) begin
            CNT <= CNT + 1;
        end
    end

endmodule
"""
    return template

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: gen_vfpga.py <dts_path>")
        sys.exit(1)
    
    dts_path = sys.argv[1]
    nodes = parse_dts(dts_path)
    
    # 1. Generate Config Header
    config_h = generate_config_h(nodes)
    os.makedirs("src/include", exist_ok=True)
    with open("src/include/vfpga_config.h", 'w') as f:
        f.write(config_h)

    # 2. Generate Shim
    shim_c = generate_shim_c(nodes)
    with open("src/shim/libfpgashim.c", 'w') as f:
        f.write(shim_c)
    
    # 3. Generate RTL
    rtl_v = generate_rtl_v(nodes)
    if rtl_v:
        with open("src/rtl/vfpga_top.v", 'w') as f:
            f.write(rtl_v)
    print("Generated Config Header, Shim, and RTL from DTS.")
