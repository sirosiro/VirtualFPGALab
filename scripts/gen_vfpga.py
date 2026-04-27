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
        
        if 'compatible' in props:
            compatible = props.get('compatible', '')
            label = props.get('label', f"/dev/{name}")
            
            node_type = 'unknown'
            if 'generic-uio' in compatible:
                node_type = 'uio'
            elif 'i2c' in compatible or 'cdns,i2c' in compatible:
                node_type = 'i2c'
            elif 'uart' in compatible or 'xlnx,xps-uart' in compatible:
                node_type = 'uart'
                
            node = {
                'name': name,
                'path': label,
                'type': node_type,
                'reg': props.get('reg', '0x0 0x0'),
                'registers': []
            }
            # Add all other props
            for k, v in props.items():
                if k not in ['label', 'compatible', 'reg', 'registers']:
                    node[k] = v
            
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
    uart_matches = []
    mmap_routes = []
    for node in nodes:
        if node['type'] == 'uio':
            reg_parts = node['reg'].split()
            if len(reg_parts) >= 2:
                base_addr = reg_parts[0]
                size = reg_parts[1]
                mmap_routes.append(f'    {{ {base_addr}, {size}, "/{node["name"]}", "{node["path"]}" }}')
        elif node['type'] == 'i2c':
            bus_id = node.get('bus_id', '1')
            i2c_matches.append(f'    if (pathname != NULL && strcmp(pathname, "{node["path"]}") == 0) return {bus_id};')
        elif node['type'] == 'uart':
            uart_matches.append(f'    if (pathname != NULL && strcmp(pathname, "{node["path"]}") == 0) return 1;')

    routes_array = ",\n".join(mmap_routes)

    template = f"""
#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>
#include <stdarg.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <termios.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <sys/ioctl.h>
#include "vfpga_config.h"

#define MAX_FDS 1024
static int virtual_fd_route_idx[MAX_FDS] = {{0}}; // 0: not virtual, >0: route index + 1, -1: /dev/mem

static int (*original_open)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*original_ioctl)(int fd, unsigned long request, void *argp) = NULL;
static void* (*original_mmap)(void *addr, size_t length, int prot, int flags, int fd, off_t offset) = NULL;

struct mmap_route {{
    unsigned long base_addr;
    unsigned long size;
    const char *shm_name;
    const char *path;
}};

static struct mmap_route routes[] = {{
{routes_array}
}};

static int find_route_by_path(const char *pathname) {{
    if (pathname == NULL) return 0;
    if (strcmp(pathname, "/dev/mem") == 0) return -1;
    for (int i = 0; i < sizeof(routes)/sizeof(routes[0]); i++) {{
        if (strcmp(pathname, routes[i].path) == 0) return i + 1;
    }}
    return 0;
}}

static int is_i2c_device(const char *pathname) {{
    if (pathname == NULL) return 0;
{chr(10).join(i2c_matches)}
    return 0;
}}

static int is_uart_device(const char *pathname) {{
    if (pathname == NULL) return 0;
{chr(10).join(uart_matches)}
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
    
    int route_idx = find_route_by_path(pathname);
    if (route_idx != 0) {{
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) virtual_fd_route_idx[fd] = route_idx;
        return fd;
    }}
    
    int i2c_bus_id = is_i2c_device(pathname);
    if (i2c_bus_id != 0) {{
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) virtual_fd_route_idx[fd] = -100 - i2c_bus_id;
        return fd;
    }}

    if (is_uart_device(pathname)) {{
        // Create a Pseudo-Terminal (PTY)
        int master_fd = posix_openpt(O_RDWR | O_NOCTTY);
        if (master_fd != -1) {{
            grantpt(master_fd);
            unlockpt(master_fd);
            char *pts_name = ptsname(master_fd);
            fprintf(stderr, "[Shim] UART MAP: %s -> %s\\n", pathname, pts_name);
            
            // Write mapping to a file for the controller to discover
            char filename[256];
            const char *leaf = strrchr(pathname, '/');
            sprintf(filename, "/tmp/vfpga_uart_%s", leaf ? leaf + 1 : pathname);
            FILE *f = fopen(filename, "w");
            if (f) {{
                fprintf(f, "%s", pts_name);
                fclose(f);
            }}
            
            if (master_fd < MAX_FDS) virtual_fd_route_idx[master_fd] = -200; // Marker for UART
        }}
        return master_fd;
    }}
    
    return original_open(pathname, flags, mode);
}}

void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset) {{
    if (!original_mmap) original_mmap = dlsym(RTLD_NEXT, "mmap");

    if (fd >= 0 && fd < MAX_FDS && virtual_fd_route_idx[fd] != 0) {{
        int route_idx = virtual_fd_route_idx[fd];
        int target_idx = -1;

        if (route_idx == -1) {{
            // /dev/mem: Search by physical address (offset)
            for (int i = 0; i < sizeof(routes)/sizeof(routes[0]); i++) {{
                if (offset >= routes[i].base_addr && offset < (routes[i].base_addr + routes[i].size)) {{
                    target_idx = i;
                    offset -= routes[i].base_addr;
                    break;
                }}
            }}
        }} else if (route_idx > 0) {{
            // Specific device (e.g. /dev/fpga0): Use fixed route
            target_idx = route_idx - 1;
        }}

        if (target_idx != -1) {{
            int shm_fd = shm_open(routes[target_idx].shm_name, O_RDWR, 0666);
            if (shm_fd == -1) return MAP_FAILED;
            void *res = original_mmap(addr, length, prot, flags, shm_fd, offset);
            close(shm_fd);
            return res;
        }}
    }}
    return original_mmap(addr, length, prot, flags, fd, offset);
}}

int ioctl(int fd, unsigned long request, ...) {{
    va_list args;
    va_start(args, request);
    void *argp = va_arg(args, void *);
    va_end(args);
    if (!original_ioctl) original_ioctl = dlsym(RTLD_NEXT, "ioctl");
    if (fd >= 0 && fd < MAX_FDS && virtual_fd_route_idx[fd] <= -101) {{
        int i2c_bus_id = -(virtual_fd_route_idx[fd] + 100);
        if (request == I2C_RDWR) {{
            struct i2c_rdwr_ioctl_data *data = (struct i2c_rdwr_ioctl_data *)argp;
            for (unsigned int i = 0; i < data->nmsgs; i++) {{
                if (data->msgs[i].flags & I2C_M_RD) {{
                    // Return dummy data based on bus_id to prove separation
                    memset(data->msgs[i].buf, 0x10 * i2c_bus_id, data->msgs[i].len);
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
    
    reg_port_list = []
    if target_node:
        for reg in target_node['registers']:
            reg_port_list.append(f"    output reg [31:0] {reg['name']}")
    
    reg_ports = ""
    if reg_port_list:
        reg_ports = ",\n" + ",\n".join(reg_port_list)

    template = f"""
/* Auto-generated RTL Skeleton from DTS */
module vfpga_top (
    input wire clk,
    input wire rst_n,
    input wire [31:0] addr,
    input wire [31:0] w_data,
    input wire w_en,
    output reg [31:0] r_data{reg_ports}
);
"""
    if target_node:
        template += """
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
"""
    else:
        template += """
    // No registers defined in DTS.
    always @(*) begin
        r_data = 32'hdeadbeef;
    end
"""
    
    template += """
endmodule
"""
    return template

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: gen_vfpga.py <dts_path>")
        sys.exit(1)
    
    dts_path = sys.argv[1]
    nodes = parse_dts(dts_path)
    for node in nodes:
        print(f"[Gen] Found node: {node['name']}, path: {node['path']}, bus_id: {node.get('bus_id', 'N/A')}")
    
    # 1. Generate Config Header
    config_h = generate_config_h(nodes)
    os.makedirs("src/include", exist_ok=True)
    with open("src/include/vfpga_config.h", 'w') as f:
        f.write(config_h)

    # 2. Generate Shim
    shim_c = generate_shim_c(nodes)
    with open("src/shim/libfpgashim.c", 'w') as f:
        f.write(shim_c)
    
    # 3. Generate RTL Skeleton
    rtl_v = generate_rtl_v(nodes)
    if rtl_v:
        with open("src/rtl/vfpga_top_skeleton.v", 'w') as f:
            f.write(rtl_v)
    print("Generated Config Header, Shim, and RTL Skeleton from DTS.")
