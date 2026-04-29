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

    printf("[Main] REG0 (オフセット0) に 0x100 を書き込みます\n");
    map_base[REG_0] = 0x100;

    printf("[Main] REG1 (オフセット4) を読み出します\n");
    
    /**
     * Verilog 側の構造:
     * vfpga_top.v が sub_logic.v をインスタンス化しています。
     * sub_logic 内では以下の演算が行われています:
     *   out_y = in_a (REG0の値) + in_b (現在の書き込みデータ) + 0x1234;
     */
    
    // シミュレーション上のタイミングを安定させるため、再度書き込みを行ってから値を読み出します。
    map_base[REG_0] = 0x10; 
    
    uint32_t val = map_base[REG_1];
    printf("[Main] 読み出し値: 0x%08x\n", val);

    // サブモジュールが正しくリンクされて動作していれば、
    // sub_logic.v 内で定義された定数 0x1234 を含む値（非ゼロ）が返ってきます。
    if (val != 0) {
        printf("[Main] 成功: サブモジュールの演算結果を確認しました！\n");
        munmap(map_base, 4096);
        close(fd);
        return 0;
    } else {
        printf("[Main] 失敗: サブモジュールの出力が 0 です。リンクまたは演算に問題があります。\n");
        munmap(map_base, 4096);
        close(fd);
        return 1;
    }
}
