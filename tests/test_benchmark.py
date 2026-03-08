"""
DHH性能基准测试
"""
import unittest
import time
import random
import tempfile
import os
from pathlib import Path

from dhh import DHHCompressor, DeltaMode
from dhh.fileio import DHHFileHandler


class TestDHHPPerformance(unittest.TestCase):
    """性能测试套件"""
    
    def setUp(self):
        self.compressor = DHHCompressor()
        self.handler = DHHFileHandler(self.compressor)
    
    def _generate_data(self, size: int, pattern: str = 'random') -> bytes:
        """生成测试数据"""
        if pattern == 'random':
            return bytes([random.randint(0, 255) for _ in range(size)])
        elif pattern == 'zeros':
            return b'\x00' * size
        elif pattern == 'ones':
            return b'\x01' * size
        elif pattern == 'sequential':
            return bytes([i % 256 for i in range(size)])
        elif pattern == 'sawtooth':
            return bytes([i % 16 for i in range(size)])
        elif pattern == 'text-like':
            # 模拟英文文本统计特征
            chars = b'etaoinshrdlcumwfgypbvkjxqzETAOINSHRDLCUMWFGYPBVKJXQZ     \n.,!?'
            weights = [12.7, 9.1, 8.2, 7.5, 7.0, 6.7, 6.3, 6.1, 6.0, 4.3, 4.0, 2.8, 2.8, 2.4, 2.2, 2.0,
                      1.9, 1.5, 1.0, 0.8, 0.15, 0.15, 0.1, 0.07, 0.02, 0.02] * 2 + [20, 15, 10, 5, 5, 5]
            return bytes(random.choices(chars, weights=weights, k=size))
        else:
            return b'\x00' * size
    
    def test_compression_speed(self):
        """测试压缩速度"""
        sizes = [1024, 10*1024, 100*1024, 1024*1024]  # 1KB to 1MB
        patterns = ['zeros', 'sequential', 'text-like', 'random']
        
        print("\n" + "="*60)
        print("压缩速度测试")
        print("="*60)
        
        for pattern in patterns:
            print(f"\n数据模式: {pattern}")
            for size in sizes:
                data = self._generate_data(size, pattern)
                
                start = time.perf_counter()
                compressed = self.compressor.compress(data)
                compress_time = time.perf_counter() - start
                
                start = time.perf_counter()
                decompressed = self.compressor.decompress(compressed)
                decompress_time = time.perf_counter() - start
                
                speed_mb_s = (size / 1024 / 1024) / compress_time
                ratio = len(compressed) / len(data)
                
                print(f"  {size//1024:5d}KB: {speed_mb_s:6.2f} MB/s, "
                      f"ratio: {ratio:.3f}, "
                      f"decompress: {decompress_time*1000:.1f}ms")
                
                self.assertEqual(data, decompressed)
    
    def test_compression_ratio(self):
        """测试不同数据类型的压缩率"""
        test_cases = [
            ('zeros', 10000, '重复零'),
            ('ones', 10000, '重复一'),
            ('sequential', 10000, '顺序递增'),
            ('sawtooth', 10000, '锯齿波'),
            ('text-like', 100000, '类文本'),
            ('random', 10000, '随机数据'),
        ]
        
        print("\n" + "="*60)
        print("压缩率测试 (10KB样本)")
        print("="*60)
        
        for pattern, size, name in test_cases:
            data = self._generate_data(size, pattern)
            compressed = self.compressor.compress(data)
            decompressed = self.compressor.decompress(compressed)
            
            ratio = len(compressed) / len(data)
            savings = (1 - ratio) * 100
            
            status = "✓" if data == decompressed else "✗"
            print(f"{status} {name:12s}: {savings:+6.1f}% "
                  f"({len(data)}B → {len(compressed)}B)")
            
            self.assertEqual(data, decompressed)
    
    def test_large_file_handling(self):
        """测试大文件处理"""
        print("\n" + "="*60)
        print("大文件处理测试 (10MB)")
        print("="*60)
        
        # 创建临时大文件
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # 写入混合数据
            for _ in range(10):  # 10MB
                chunk = self._generate_data(1024*1024, 'text-like')
                tmp.write(chunk)
            tmp_path = tmp.name
        
        try:
            compressed_path = tmp_path + ".dhh"
            restored_path = tmp_path + ".restored"
            
            # 流式压缩
            print("流式压缩...")
            start = time.perf_counter()
            stats = self.handler.compress_file(tmp_path, compressed_path, 
                                              use_streaming=True)
            compress_time = time.perf_counter() - start
            
            print(f"  原始: {stats['original_size']//1024//1024}MB, "
                  f"压缩后: {stats['compressed_size']//1024}KB, "
                  f"时间: {compress_time:.2f}s")
            
            # 解压
            print("解压...")
            start = time.perf_counter()
            self.handler.decompress_file(compressed_path, restored_path)
            decompress_time = time.perf_counter() - start
            print(f"  时间: {decompress_time:.2f}s")
            
            # 验证
            with open(tmp_path, 'rb') as f1, open(restored_path, 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())
            print("  ✓ 完整性验证通过")
            
        finally:
            for path in [tmp_path, compressed_path, restored_path]:
                if os.path.exists(path):
                    os.remove(path)
    
    def test_memory_efficiency(self):
        """测试内存使用（粗略估计）"""
        import sys
        
        print("\n" + "="*60)
        print("内存使用测试")
        print("="*60)
        
        # 测试不同大小数据的内存占用
        sizes = [1024, 10*1024, 100*1024]
        
        for size in sizes:
            data = self._generate_data(size, 'text-like')
            
            # 压缩前内存
            mem_before = sys.getsizeof(data)
            
            compressed = self.compressor.compress(data)
            mem_compressed = sys.getsizeof(compressed)
            
            # 删除中间变量，强制垃圾回收
            import gc
            gc.collect()
            
            decompressed = self.compressor.decompress(compressed)
            mem_decompressed = sys.getsizeof(decompressed)
            
            print(f"{size//1024:5d}KB: "
                  f"原始={mem_before}B, "
                  f"压缩后={mem_compressed}B, "
                  f"解压后={mem_decompressed}B")
            
            self.assertEqual(data, decompressed)
            del data, compressed, decompressed
            gc.collect()
    
    def test_delta_modes(self):
        """测试不同Delta模式的性能"""
        print("\n" + "="*60)
        print("Delta模式对比")
        print("="*60)
        
        # 生成适合二阶差分的数据（平滑变化）
        size = 100000
        smooth_data = bytes([int(128 + 50 * (i / 1000)) % 256 
                            for i in range(size)])
        
        for mode in [DeltaMode.SIMPLE, DeltaMode.DOUBLE]:
            compressor = DHHCompressor(mode=mode)
            
            start = time.perf_counter()
            compressed = compressor.compress(smooth_data)
            compress_time = time.perf_counter() - start
            
            start = time.perf_counter()
            decompressed = compressor.decompress(compressed)
            decompress_time = time.perf_counter() - start
            
            ratio = len(compressed) / len(smooth_data)
            
            print(f"{mode.name:10s}: ratio={ratio:.3f}, "
                  f"compress={compress_time*1000:.1f}ms, "
                  f"decompress={decompress_time*1000:.1f}ms")
            
            self.assertEqual(smooth_data, decompressed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
