#!/usr/bin/env python3
import re
import os
import sys

# =============================================================================
# 1. Data Models
# =============================================================================

class Register:
    def __init__(self, name, offset, direction='RW'):
        self.name = name
        self.offset = offset
        self.direction = direction.upper()

class Device:
    def __init__(self, name, path, dev_type, base_reg):
        self.name = name
        self.path = path
        self.type = dev_type
        self.base_reg = base_reg
        self.registers = []
        self.extra_props = {}
        # Parse size from base_reg (e.g. "0x40000000 0x1000")
        try:
            parts = base_reg.split()
            self.size = int(parts[1], 0) if len(parts) >= 2 else 0
        except:
            self.size = 0

class BoardModel:
    def __init__(self, devices, name="vfpga"):
        self.devices = devices
        self.name = name
    def get_uio_device(self):
        return next((d for d in self.devices if d.type == 'uio'), None)

# =============================================================================
# 2. Parser
# =============================================================================

class DTSParser:
    @staticmethod
    def parse(dts_path):
        with open(dts_path, 'r') as f:
            content = f.read()
        devices = []
        matches = re.finditer(r'([a-zA-Z0-9_@]+)\s*\{([^}]+)\}', content)
        for match in matches:
            raw_name = match.group(1).strip()
            name = raw_name.split('@')[0]
            body = match.group(2)
            props = {}
            prop_matches = re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*([^;]+);', body)
            for p_match in prop_matches:
                k = p_match.group(1).strip()
                v = p_match.group(2).strip()
                if v.startswith('<') and v.endswith('>'): v = v[1:-1].strip()
                if v.startswith('"') and v.endswith('"'): v = v[1:-1].strip()
                props[k] = v
            if 'compatible' in props:
                compatible = props.get('compatible', '')
                label = props.get('label', "/dev/%s" % name)
                dev_type = 'unknown'
                if 'generic-uio' in compatible: dev_type = 'uio'
                elif 'i2c' in compatible or 'cdns,i2c' in compatible: dev_type = 'i2c'
                elif 'uart' in compatible or 'xlnx,xps-uart' in compatible: dev_type = 'uart'
                elif 'gpio' in compatible or 'xlnx,xps-gpio' in compatible: dev_type = 'gpio'
                device = Device(name, label, dev_type, props.get('reg', '0x0 0x0'))
                for k, v in props.items():
                    if k not in ['label', 'compatible', 'reg', 'registers']: device.extra_props[k] = v
                if 'registers' in props:
                    reg_raw = props['registers'].replace('\\n', ' ').replace('\\"', '').replace('\\t', ' ')
                    reg_list = reg_raw.split(',')
                    for r_str in reg_list:
                        r_str = r_str.strip().strip('"').strip()
                        if '@' in r_str:
                            reg_parts = r_str.split('@')
                            reg_name = reg_parts[0].strip()
                            reg_offset = reg_parts[1].strip()
                            device.registers.append(Register(reg_name, reg_offset, 'RW'))
                devices.append(device)
        
        # 共有メモリ名として使用するボード名を決定（UIOデバイス名があれば優先）
        board_name = "vfpga_reg"
        uio = next((d for d in devices if d.type == 'uio'), None)
        if uio: board_name = uio.name
        
        return BoardModel(devices, name=board_name)

# =============================================================================
# 3. Generators
# =============================================================================

class BaseGenerator:
    def generate(self, model: BoardModel):
        raise NotImplementedError

class ConfigGenerator(BaseGenerator):
    def generate(self, model: BoardModel):
        uio_node = model.get_uio_device()
        shm_name = uio_node.name if uio_node else "vfpga_reg"
        shm_size = uio_node.size if uio_node else 1024
        # プロジェクトルートを動的に取得
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        
        return """/* Auto-generated Config from DTS */
#ifndef VFPGA_CONFIG_H
#define VFPGA_CONFIG_H
#define PROJECT_ROOT "%s"
#define SHM_NAME "%s"
#define SHM_FILE "/tmp/%s"
#define SHM_SIZE %d
#endif
""" % (project_root, shm_name, shm_name, shm_size)

class ShimGenerator(BaseGenerator):
    def generate(self, model: BoardModel):
        mmap_routes, i2c_matches, uart_matches = [], [], []
        for i, dev in enumerate(model.devices):
            if dev.type in ['uio', 'gpio']:
                reg_parts = dev.base_reg.split()
                if len(reg_parts) >= 2:
                    mmap_routes.append('    { %s, %s, SHM_FILE, "%s" }' % (reg_parts[0], reg_parts[1], dev.path))
            elif dev.type == 'i2c':
                bus_id = dev.extra_props.get('bus_id', '1')
                i2c_matches.append('    if (pathname != NULL && strcmp(pathname, "%s") == 0) return %s;' % (dev.path, bus_id))
            elif dev.type == 'uart':
                uart_matches.append('    if (pathname != NULL && strcmp(pathname, "%s") == 0) return %d;' % (dev.path, i + 1))
        
        return """
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
#include <errno.h>
#include "vfpga_config.h"

#define MAX_FDS 1024
static int virtual_fd_route_idx[MAX_FDS] = {0};

static int (*original_open)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*original_ioctl)(int fd, unsigned long request, void *argp) = NULL;
static void* (*original_mmap)(void *addr, size_t length, int prot, int flags, int fd, off_t offset) = NULL;

struct mmap_route { unsigned long base_addr; unsigned long size; const char *shm_path; const char *path; };
static struct mmap_route routes[] = { %s };

static int find_route_by_path(const char *pathname) {
    if (pathname == NULL) return 0;
    if (strcmp(pathname, "/dev/mem") == 0) return -1;
    for (int i = 0; i < (int)(sizeof(routes)/sizeof(routes[0])); i++)
        if (strcmp(pathname, routes[i].path) == 0) return i + 1;
    return 0;
}

static int is_i2c_device(const char *pathname) { (void)pathname; %s return 0; }
static int is_uart_device(const char *pathname) { (void)pathname; %s return 0; }

int open(const char *pathname, int flags, ...) {
    mode_t mode = 0; if (flags & O_CREAT) { va_list arg; va_start(arg, flags); mode = va_arg(arg, mode_t); va_end(arg); }
    if (!original_open) original_open = dlsym(RTLD_NEXT, "open");
    int route_idx = find_route_by_path(pathname);
    if (route_idx != 0) {
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) virtual_fd_route_idx[fd] = route_idx;
        return fd;
    }
    int i2c_bus_id = is_i2c_device(pathname);
    if (i2c_bus_id != 0) {
        int fd = original_open("/dev/null", flags, mode);
        if (fd != -1 && fd < MAX_FDS) virtual_fd_route_idx[fd] = -100 - i2c_bus_id;
        return fd;
    }
    int uart_id = is_uart_device(pathname);
    if (uart_id != 0) {
        int master_fd = posix_openpt(O_RDWR | O_NOCTTY);
        if (master_fd != -1) {
            grantpt(master_fd); unlockpt(master_fd);
            char *slave_name = ptsname(master_fd);
            if (slave_name) {
                char map_path[512];
                snprintf(map_path, sizeof(map_path), "%%s/dashboard/data/vfpga_uart_%%d", PROJECT_ROOT, uart_id);
                int map_fd = original_open(map_path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
                if (map_fd != -1) {
                    write(map_fd, slave_name, strlen(slave_name));
                    close(map_fd);
                }
            }
            if (master_fd < MAX_FDS) virtual_fd_route_idx[master_fd] = -200;
        }
        return master_fd;
    }
    return original_open(pathname, flags, mode);
}

void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset) {
    if (!original_mmap) original_mmap = dlsym(RTLD_NEXT, "mmap");
    if (fd >= 0 && fd < MAX_FDS && virtual_fd_route_idx[fd] != 0) {
        int route_idx = virtual_fd_route_idx[fd];
        int target_idx = -1;
        if (route_idx == -1) {
            for (int i = 0; i < (int)(sizeof(routes)/sizeof(routes[0])); i++) {
                if ((unsigned long)offset >= routes[i].base_addr && (unsigned long)offset < (routes[i].base_addr + routes[i].size)) {
                    target_idx = i; offset -= (off_t)routes[i].base_addr; break;
                }
            }
        } else if (route_idx > 0) target_idx = route_idx - 1;
        
        if (target_idx != -1) {
            int shm_fd = original_open(routes[target_idx].shm_path, O_RDWR, 0666);
            if (shm_fd < 0) {
                fprintf(stderr, "[Shim] ERROR: Failed to open %%s! (errno: %%d)\\n", routes[target_idx].shm_path, errno);
            } else {
                void *res = original_mmap(addr, length, prot, flags, shm_fd, offset);
                if (res == MAP_FAILED) {
                    fprintf(stderr, "[Shim] ERROR: original_mmap failed! (shm_fd: %%d, length: %%zu, errno: %%d)\\n", shm_fd, length, errno);
                }
                close(shm_fd); 
                return res;
            }
        }
    }
    return original_mmap(addr, length, prot, flags, fd, offset);
}

int ioctl(int fd, unsigned long request, ...) {
    va_list args; va_start(args, request); void *argp = va_arg(args, void *); va_end(args);
    if (!original_ioctl) original_ioctl = dlsym(RTLD_NEXT, "ioctl");
    if (fd >= 0 && fd < MAX_FDS && virtual_fd_route_idx[fd] <= -101) {
        int i2c_bus_id = -(virtual_fd_route_idx[fd] + 100);
        if (request == I2C_RDWR) {
            struct i2c_rdwr_ioctl_data *data = (struct i2c_rdwr_ioctl_data *)argp;
            for (unsigned int i = 0; i < data->nmsgs; i++)
                if (data->msgs[i].flags & I2C_M_RD) memset(data->msgs[i].buf, 0x10 * i2c_bus_id, data->msgs[i].len);
            return 0;
        }
        if (request == I2C_SLAVE || request == I2C_SLAVE_FORCE) return 0;
    }
    return original_ioctl(fd, request, argp);
}
""" % (", ".join(mmap_routes), " ".join(i2c_matches), " ".join(uart_matches))

class RTLGenerator(BaseGenerator):
    def generate(self, model: BoardModel):
        uio_dev = model.get_uio_device()
        if not uio_dev: return """/* verilator lint_off UNUSED */
module vfpga_top (
    input wire clk, input wire rst_n, input wire [31:0] addr, 
    input wire [31:0] w_data, input wire w_en, output reg [31:0] r_data
);
    always @(*) r_data = 32'hdeadbeef;
endmodule"""
        reg_ports = ",\n".join(['    output reg [31:0] %s' % r.name for r in uio_dev.registers])
        reset_logic = "\n".join(['            %s <= 32\'h0;' % r.name for r in uio_dev.registers])
        write_cases = "\n".join(['                %s: %s <= w_data;' % (r.offset.replace('0x', "32'h"), r.name) for r in uio_dev.registers])
        read_cases = "\n".join(['            %s: r_data = %s;' % (r.offset.replace('0x', "32'h"), r.name) for r in uio_dev.registers])
        return """/* Auto-generated RTL Skeleton */
module vfpga_top (
    input wire clk, input wire rst_n, input wire [31:0] addr, input wire [31:0] w_data, input wire w_en, output reg [31:0] r_data%s
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
%s
        end else if (w_en) begin
            case (addr)
%s
                default: ;
            endcase
        end
    end
    always @(*) begin
        case (addr)
%s
            default: r_data = 32'hdeadbeef;
        endcase
    end
endmodule
""" % (("," + reg_ports) if reg_ports else "", reset_logic, write_cases, read_cases)

class SimulatorGenerator(BaseGenerator):
    def generate(self, model: BoardModel):
        uio_dev = model.get_uio_device()
        reg_defs = ['    { .name="%s", .offset=%s }' % (r.name, r.offset) for r in uio_dev.registers] if uio_dev else []
        return """
#include <stdio.h>
#include <iostream>
#include <verilated.h>
#include "Vvfpga_top.h"
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <verilated_vcd_c.h>
#include "vfpga_config.h"

struct RegMeta { const char* name; uint32_t offset; };
static RegMeta registers[] = { %s };

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vvfpga_top* top = new Vvfpga_top;
    int fd = open(SHM_FILE, O_CREAT | O_RDWR, 0666);
    if (ftruncate(fd, SHM_SIZE) == -1) {
        perror("ftruncate");
        return 1;
    }
    uint32_t* shm = (uint32_t*)mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    uint32_t old_shm[SHM_SIZE/4]; memset(old_shm, 0, SHM_SIZE);

    Verilated::traceEverOn(true);
    VerilatedVcdC* m_trace = new VerilatedVcdC;
    top->trace(m_trace, 99);
    m_trace->open("vfpga.vcd");
    uint64_t vtime = 0;
    
    top->rst_n = 1; top->clk = 0; top->eval(); m_trace->dump(vtime++);
    top->rst_n = 0; top->eval(); top->clk = 1; top->eval(); top->clk = 0; top->eval(); m_trace->dump(vtime++);
    top->rst_n = 1; top->eval(); m_trace->dump(vtime++);

    printf("[Sim] Simulator Started (SHM: %%s)\\n", SHM_FILE); fflush(stdout);
    while (!Verilated::gotFinish()) {
        for (int i = 0; i < %d; i++) {
            uint32_t off = registers[i].offset / 4;
            if (shm[off] != old_shm[off]) {
                top->addr = registers[i].offset; top->w_data = shm[off]; top->w_en = 1;
                top->eval(); top->clk = 1; top->eval(); top->clk = 0; top->eval();
                top->w_en = 0; old_shm[off] = shm[off];
            }
        }
        for (int i = 0; i < %d; i++) {
            top->addr = registers[i].offset; top->eval();
            uint32_t off = registers[i].offset / 4;
            if (top->r_data != old_shm[off]) {
                shm[off] = top->r_data; old_shm[off] = top->r_data;
            }
        }
        top->eval(); top->clk = 1; top->eval(); top->clk = 0; top->eval();
        m_trace->dump(vtime++);
        usleep(100);
    }
    m_trace->close();
    return 0;
}
""" % (", ".join(reg_defs), len(reg_defs), len(reg_defs))

class ManifestGenerator(BaseGenerator):
    def generate(self, model: BoardModel):
        import json
        uio = model.get_uio_device()
        shm_name = uio.name if uio else "vfpga_reg"
        shm_size = uio.size if uio else 1024
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        manifest = {
            "board": shm_name,
            "shm_path": f"/tmp/{shm_name}",
            "shm_size": shm_size,
            "project_root": project_root,
            "devices": []
        }
        for dev in model.devices:
            dev_info = {
                "name": dev.name,
                "type": dev.type,
                "path": dev.path,
                "base_reg": dev.base_reg,
                "registers": [{"name": r.name, "offset": r.offset} for r in dev.registers],
                "extra": dev.extra_props
            }
            manifest["devices"].append(dev_info)
        return json.dumps(manifest, indent=4)

class GeneratorOrchestrator:
    def __init__(self, model: BoardModel):
        self.model = model
        # プロジェクトルートを取得
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        self.generators = {
            "src/include/vfpga_config.h": ConfigGenerator(),
            "src/shim/libfpgashim.c": ShimGenerator(),
            "src/rtl/vfpga_top.v": RTLGenerator(),
            "src/sim/sim_main.cpp": SimulatorGenerator(),
            "dashboard/data/board_manifest.json": ManifestGenerator()
        }
    def generate_all(self):
        for rel_path, gen in self.generators.items():
            content = gen.generate(self.model)
            # 絶対パスを構築
            abs_path = os.path.join(self.project_root, rel_path)
            dir_name = os.path.dirname(abs_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(content)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    model = DTSParser.parse(sys.argv[1])
    GeneratorOrchestrator(model).generate_all()
