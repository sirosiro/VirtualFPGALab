CC = gcc
CFLAGS = -Wall -Wextra -fPIC -Isrc/include
LDFLAGS = -shared -ldl

SHIM_SRC = src/shim/libfpgashim.c
SHIM_OUT = libfpgashim.so
GEN_SCRIPT = scripts/gen_vfpga.py
RTL_TOP = src/rtl/vfpga_top.v

# Configuration (Defaults to tests/vfpga_config.dts)
CONFIG ?= tests/vfpga_config.dts

# Verilator
VERILATOR = verilator
VERILATOR_FLAGS = -Wall --cc --exe -CFLAGS "-I../src/include"
SIM_SRC = src/sim/counter_sim.cpp
SIM_OUT = obj_dir/Vvfpga_top

all: engine

# Generate Shim, Header, and RTL from the selected DTS
$(SHIM_SRC) $(RTL_TOP) src/include/vfpga_config.h: $(CONFIG) $(GEN_SCRIPT)
	python3 $(GEN_SCRIPT) $(CONFIG)

# Build the Interception Shim
$(SHIM_OUT): $(SHIM_SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

# Build the Verilator Simulator
$(SIM_OUT): $(RTL_TOP) $(SIM_SRC)
	$(VERILATOR) $(VERILATOR_FLAGS) $(RTL_TOP) $(SIM_SRC)
	$(MAKE) -C obj_dir -f Vvfpga_top.mk

engine: $(SHIM_OUT) $(SIM_OUT)

clean:
	rm -f $(SHIM_OUT)
	rm -f $(SHIM_SRC) $(RTL_TOP) src/include/vfpga_config.h
	rm -rf obj_dir
	$(MAKE) -C tests clean || true
	$(MAKE) -C sandbox clean || true

# Helper for Docker
docker-up:
	docker compose up --build

docker-down:
	docker compose down

.PHONY: all engine clean verilate docker-up docker-down
