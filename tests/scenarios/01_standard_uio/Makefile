# F-BB: Scenario Makefile
TARGET = test_bin

# コンパイラ設定 (?= を使うことで、PetaLinux等の環境変数を優先できる)
CC ?= gcc
CFLAGS += -Wall -Wextra -I../../../src/include

# ディレクトリ内の全ての .c ファイルを対象にする
SRCS = $(wildcard *.c)
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(TARGET) $(OBJS)

.PHONY: all clean
