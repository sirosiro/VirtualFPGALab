#include <stdio.h>
#include <stdint.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>

/**
 * シナリオ 05: 複数 Verilog ファイル構成のテスト
 * 
 * @intent:responsibility 複数Verilogファイル構成のビルドと結合が正しく機能しているかを検証する。
 * @intent:rationale サブモジュール（sub_logic.v）内にのみ存在する定数（0x1234）が読み出し値に含まれることを確認することで、
 *                   単体ファイルではなく、複数ファイルのリンクとインスタンス化が成功したことを実証する。
 */

#define DEV_ADDR 0x40000000
#define REG_0    0
#define REG_1    1 // オフセット 4

int main() {
    // 物理メモリ空間（/dev/mem）へのアクセス。
    // VirtualFPGALab の Shim 層がこれをインターセプトし、仮想的な共有メモリへリダイレクトします。
    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    // FPGAのレジスタ領域（4KB）をプロセス空間にマップします。
    uint32_t *map_base = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, DEV_ADDR);
    if (map_base == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }

    // テスト用の値を書き込みます
    uint32_t test_val = 0x1000;
    uint32_t expected = test_val + 0x1234; // RTL: reg0 + 0x0 + 0x1234

    printf("[Main] REG0 (オフセット0) に 0x%08x を書き込みます\n", test_val);
    map_base[REG_0] = test_val;

    // 【解説: シミュレーション用の待機】
    // 実機(FPGA)では、ハードウェアの演算速度がCPUの命令実行速度を遥かに上回るため、
    // このような単純な加算処理に待機は不要です。しかし本環境では、アプリとシミュレータが
    // 別プロセスで動作しており、シミュレータが共有メモリの変化を検知して仮想クロックを
    // 進めるまでに物理的な時間差が生じるため、正確な結果を読み取るために待機を設けています。
    usleep(1000);

    printf("[Main] REG1 (オフセット4) から演算結果を読み出します\n");
    uint32_t val = map_base[REG_1];
    printf("[Main] 読み出し値: 0x%08x (期待値: 0x%08x)\n", val, expected);

    if (val == expected) {
        printf("[Main] 成功: サブモジュールの正確な演算結果を確認しました！\n");
        munmap(map_base, 4096);
        close(fd);
        return 0;
    } else {
        printf("[Main] 失敗: 演算結果が不正確です (期待値: 0x%08x, 実測値: 0x%08x)\n", expected, val);
        munmap(map_base, 4096);
        close(fd);
        return 1;
    }
}
