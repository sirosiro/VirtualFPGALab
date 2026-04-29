#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

/**
 * 【解説: UART(シリアルポート)の制御】
 * FPGA上のUARTは、Linuxからは「TTYデバイス」というキャラクターデバイスの一種として見えます。
 * 特殊なライブラリは不要で、標準的なファイル操作APIで読み書きできます。
 */
int main() {
    printf("--- UART Access Test Start ---\n");

    // 【解説: デバイスのオープン】
    // /dev/ttyPS2 をオープンします。
    // O_NOCTTY は、「このデバイスをプロセスの制御端末（Control Terminal）にしない」という
    // シリアルポートを開く際の標準的なお作法です。
    printf("[App] Opening /dev/ttyPS2...\n");
    int fd = open("/dev/ttyPS2", O_RDWR | O_NOCTTY);
    if (fd < 0) {
        perror("open");
        printf("[App] FAILURE: Could not open /dev/ttyPS2\n");
        return 1;
    }

    printf("[App] Successfully opened /dev/ttyPS2\n");

    // 【解説: データの送信】
    // write システムコールを呼ぶだけで、UARTの送信レジスタ（TX）にデータが送られます。
    const char *msg = "Hello from Virtual FPGA UART!\r\n";
    printf("[App] Sending: %s", msg);
    
    ssize_t written = write(fd, msg, strlen(msg));
    if (written < 0) {
        perror("write");
        close(fd);
        return 1;
    }

    printf("[App] Successfully wrote %zd bytes to UART\n", written);

    // 【解説: 後始末】
    // 通信が終わったら close を呼びます。
    close(fd);
    printf("--- UART Access Test End ---\n");
    return 0;
}
