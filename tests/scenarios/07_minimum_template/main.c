#include <stdio.h>
#include <unistd.h>

/**
 * Minimal Firmware for Minimum Template
 * 
 * このプログラムは何もせず、シミュレーションが走る時間を稼ぐだけです。
 * シミュレーション中に生成される vfpga.vcd を確認してください。
 */
int main() {
    printf("[Minimum Template] Starting minimal simulation...\n");
    printf("[Minimum Template] Simulation is running in the background.\n");
    printf("[Minimum Template] Waiting 5 seconds for waveform generation...\n");
    
    sleep(5);
    
    printf("[Minimum Template] Done. Check vfpga.vcd using GTKWave.\n");
    return 0;
}
