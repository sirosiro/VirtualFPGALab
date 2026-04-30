const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
app.use(cors());
const server = http.createServer(app);
const io = new Server(server, {
    cors: { origin: "*" }
});

const MANIFEST_PATH = path.join(__dirname, 'data/board_manifest.json');
let manifest = {};
let shmBuffer = null;

// マニフェストの読み込み
function loadManifest() {
    try {
        if (fs.existsSync(MANIFEST_PATH)) {
            const data = fs.readFileSync(MANIFEST_PATH, 'utf8');
            manifest = JSON.parse(data);
            console.log(`[Backend] Manifest loaded: ${manifest.board}`);
            return true;
        }
    } catch (e) {
        console.error(`[Backend] Failed to load manifest: ${e.message}`);
    }
    return false;
}

// 共有メモリの読み取り
function updateShm() {
    if (!manifest.shm_path) return;
    try {
        if (fs.existsSync(manifest.shm_path)) {
            const stats = fs.statSync(manifest.shm_path);
            if (stats.size > 0) {
                shmBuffer = fs.readFileSync(manifest.shm_path);
                broadcastRegisters();
            }
        }
    } catch (e) {
        // 静かに無視（ファイルがまだ作成されていない場合など）
    }
}

// レジスタ情報のブロードキャスト
function broadcastRegisters() {
    if (!shmBuffer || !manifest.devices) return;
    
    const regData = [];
    manifest.devices.forEach(dev => {
        if (dev.type === 'uio') {
            dev.registers.forEach(reg => {
                const offset = parseInt(reg.offset, 0);
                if (offset + 4 <= shmBuffer.length) {
                    const value = shmBuffer.readUInt32LE(offset);
                    regData.push({
                        name: reg.name,
                        offset: reg.offset,
                        value: `0x${value.toString(16).padStart(8, '0')}`,
                        decimal: value,
                        deviceName: dev.name
                    });
                }
            });
        }
    });
    io.emit('registers', regData);
}

// 定期実行
setInterval(() => {
    if (Object.keys(manifest).length === 0) {
        loadManifest();
    }
    updateShm();
}, 200); // 200ms間隔で更新

// APIエンドポイント
app.get('/api/manifest', (req, res) => {
    res.json(manifest);
});

// フロントエンドの静的ファイル（ビルド後用）
app.use(express.static(path.join(__dirname, 'client/dist')));

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
    console.log(`[Backend] Dashboard Server running on http://localhost:${PORT}`);
});
