CC = gcc
CFLAGS = -Wall -Wextra -I../src/include

# Outputs
TARGETS = test_open test_shm test_reg_access test_i2c test_verilator test_dev_mem test_multi_i2c test_legacy_style test_uart

all: $(TARGETS)

test_open: test_open.c
	$(CC) $(CFLAGS) -o $@ $<

test_shm: test_shm.c
	$(CC) $(CFLAGS) -o $@ $< -lrt

test_reg_access: test_reg_access.c
	$(CC) $(CFLAGS) -o $@ $<

test_i2c: test_i2c.c
	$(CC) $(CFLAGS) -o $@ $<

test_verilator: test_verilator.c
	$(CC) $(CFLAGS) -o $@ $<

test_dev_mem: test_dev_mem.c
	$(CC) $(CFLAGS) -o $@ $< -lrt

test_multi_i2c: test_multi_i2c.c
	$(CC) $(CFLAGS) -o $@ $<

test_legacy_style: test_legacy_style.c
	$(CC) $(CFLAGS) -o $@ $<

test_uart: test_uart.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(TARGETS)

.PHONY: all clean
