CC = gcc
CFLAGS = -Wall -Wextra -I../../src/include
LDFLAGS = 

TARGET = test_bin
SRCS = main.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGET)
