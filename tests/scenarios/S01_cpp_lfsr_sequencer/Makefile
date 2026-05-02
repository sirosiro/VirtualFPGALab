CXX = g++
CXXFLAGS = -Wall -Wextra -O2 -std=c++17
TARGET = test_bin
SRCS = main.cpp

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) $(SRCS) -o $(TARGET)

clean:
	rm -f $(TARGET)
