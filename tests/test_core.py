import unittest
import os
import tempfile
from dhh import DHHCompressor, DeltaMode


class TestDHHCompressor(unittest.TestCase):
    
    def setUp(self):
        self.compressor = DHHCompressor()
    
    def test_empty_data(self):
        """测试空数据"""
        data = b''
        compressed = self.compressor.compress(data)
        decompressed = self.compressor.decompress(compressed)
        self.assertEqual(data, decompressed)
    
    def test_single_byte(self):
        """测试单字节"""
        data = b'A'
        compressed = self.compressor.compress(data)
        decompressed = self.compressor.decompress(compressed)
        self.assertEqual(data, decompressed)
    
    def test_repeated_bytes(self):
        """测试重复字节（高压缩率场景）"""
        data = b'A' * 1000
        compressed = self.compressor.compress(data)
        decompressed = self.compressor.decompress(compressed)
        self.assertEqual(data, decompressed)
        self.assertLess(len(compressed), len(data))
    
    def test_incremental_sequence(self):
        """测试递增序列"""
        data = bytes(range(256)) * 4
        compressed = self.compressor.compress(data)
        decompressed = self.compressor.decompress(compressed)
        self.assertEqual(data, decompressed)
    
    def test_random_data(self):
        """测试随机数据（完整性验证）"""
        import random
        random.seed(42)
        data = bytes([random.randint(0, 255) for _ in range(1000)])
        compressed = self.compressor.compress(data)
        decompressed = self.compressor.decompress(compressed)
        self.assertEqual(data, decompressed)
    
    def test_text_data(self):
        """测试文本数据"""
        data = b"Hello, World! " * 100
        compressed = self.compressor.compress(data)
        decompressed = self.compressor.decompress(compressed)
        self.assertEqual(data, decompressed)
    
    def test_file_operations(self):
        """测试文件压缩/解压"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_in:
            tmp_in.write(b"Test data for file operations " * 50)
            input_path = tmp_in.name
        
        output_path = input_path + ".dhh"
        restore_path = input_path + ".restored"
        
        try:
            # 压缩
            stats = self.compressor.compress_file(input_path, output_path)
            self.assertIn('ratio', stats)
            
            # 解压
            self.compressor.decompress_file(output_path, restore_path)
            
            # 验证
            with open(input_path, 'rb') as f:
                original = f.read()
            with open(restore_path, 'rb') as f:
                restored = f.read()
            self.assertEqual(original, restored)
            
        finally:
            for path in [input_path, output_path, restore_path]:
                if os.path.exists(path):
                    os.remove(path)


if __name__ == '__main__':
    unittest.main()
