import unittest
import os
import sys
from gen_vfpga import DTSParser, BoardModel, ConfigGenerator, ShimGenerator, RTLGenerator

class TestVFPGAEngine(unittest.TestCase):
    def setUp(self):
        self.sample_dts = """
        / {
            vfpga_reg@40000000 {
                compatible = "generic-uio";
                reg = <0x40000000 0x1000>;
                label = "/dev/uio0";
                registers = "EN@0x14, RST@0x10";
            };
            i2c_test@50000000 {
                compatible = "cdns,i2c-r1p10";
                reg = <0x50000000 0x100>;
                label = "/dev/i2c-1";
                bus_id = "1";
            };
        };
        """
        # テンポラリなDTSファイルを作成
        with open("test_sample.dts", "w") as f:
            f.write(self.sample_dts)

    def tearDown(self):
        if os.path.exists("test_sample.dts"):
            os.remove("test_sample.dts")

    def test_parser(self):
        model = DTSParser.parse("test_sample.dts")
        self.assertEqual(len(model.devices), 2)
        
        uio = model.get_uio_device()
        self.assertIsNotNone(uio)
        self.assertEqual(uio.name, "vfpga_reg")
        self.assertEqual(uio.path, "/dev/uio0")
        
        # レジスタが正しくパースされているか
        reg_names = [r.name for r in uio.registers]
        self.assertIn("EN", reg_names)
        self.assertIn("RST", reg_names)
        
        # I2C デバイスの確認
        i2c = next(d for d in model.devices if d.type == "i2c")
        self.assertEqual(i2c.extra_props["bus_id"], "1")

    def test_config_generator(self):
        model = DTSParser.parse("test_sample.dts")
        gen = ConfigGenerator()
        content = gen.generate(model)
        self.assertIn("#define SHM_PATH \"/tmp/vfpga_reg\"", content)
        self.assertIn("#define SHM_SIZE 1024", content)

    def test_shim_generator(self):
        model = DTSParser.parse("test_sample.dts")
        gen = ShimGenerator()
        content = gen.generate(model)
        # MMAP ルートの確認
        self.assertIn("{ 0x40000000, 0x1000, SHM_PATH, \"/dev/uio0\" }", content)
        # I2C マッチングの確認
        self.assertIn("strcmp(pathname, \"/dev/i2c-1\") == 0", content)
        # 基本的な関数の存在確認
        self.assertIn("int open(const char *pathname, int flags, ...)", content)
        self.assertIn("void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset)", content)

    def test_rtl_generator(self):
        model = DTSParser.parse("test_sample.dts")
        gen = RTLGenerator()
        content = gen.generate(model)
        self.assertIn("module vfpga_top", content)
        self.assertIn("output reg [31:0] EN", content)
        self.assertIn("output reg [31:0] RST", content)
        self.assertIn("32'h14: EN <= w_data;", content)

if __name__ == "__main__":
    unittest.main()
