CC = gcc
CFLAGS = -Wall -Wextra -fPIC
LDFLAGS = -shared -ldl

SHIM_SRC = src/shim/libfpgashim.c
SHIM_OUT = libfpgashim.so

TEST_SRC = tests/test_open.c
TEST_OUT = tests/test_open

TEST_SHM_SRC = tests/test_shm.c
TEST_SHM_OUT = tests/test_shm

TEST_REG_SRC = tests/test_reg_access.c
TEST_REG_OUT = tests/test_reg_access

TEST_I2C_SRC = tests/test_i2c.c
TEST_I2C_OUT = tests/test_i2c

TEST_VER_SRC = tests/test_verilator.c
TEST_VER_OUT = tests/test_verilator

# Verilator
VERILATOR = verilator
VERILATOR_FLAGS = -Wall --cc --exe
RTL_SRC = src/rtl/counter.v
SIM_SRC = src/sim/counter_sim.cpp
SIM_OUT = obj_dir/Vcounter

all: $(SHIM_OUT) $(TEST_OUT) $(TEST_SHM_OUT) $(TEST_REG_OUT) $(TEST_I2C_OUT) $(TEST_VER_OUT) verilate

$(SHIM_OUT): $(SHIM_SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

$(TEST_OUT): $(TEST_SRC)
	$(CC) $(CFLAGS) -o $@ $<

$(TEST_SHM_OUT): tests/test_shm.c
	$(CC) $(CFLAGS) -o $@ $< -lrt

$(TEST_REG_OUT): $(TEST_REG_SRC)
	$(CC) $(CFLAGS) -o $@ $<

$(TEST_I2C_OUT): $(TEST_I2C_SRC)
	$(CC) $(CFLAGS) -o $@ $<

$(TEST_VER_OUT): $(TEST_VER_SRC)
	$(CC) $(CFLAGS) -o $@ $<

$(SIM_OUT): $(RTL_SRC) $(SIM_SRC)
	$(VERILATOR) $(VERILATOR_FLAGS) $(RTL_SRC) $(SIM_SRC)
	$(MAKE) -C obj_dir -f Vcounter.mk

verilate: $(SIM_OUT)

clean:
	rm -f $(SHIM_OUT) $(TEST_OUT) $(TEST_SHM_OUT) $(TEST_REG_OUT) $(TEST_I2C_OUT) $(TEST_VER_OUT)
	rm -rf obj_dir

.PHONY: all clean verilate
