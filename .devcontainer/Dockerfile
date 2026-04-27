FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install basic build tools and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    pkg-config \
    libfl-dev \
    zlib1g-dev \
    libgoogle-perftools-dev \
    numactl \
    perl \
    python3 \
    python3-pip \
    python3-dev \
    gdb \
    strace \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Verilator
RUN apt-get update && apt-get install -y verilator

# Install Python packages for visualization and testing
RUN pip3 install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    pytest \
    flask \
    flask-cors

# Set workspace directory
WORKDIR /workspace
