#!/usr/bin/env python3
"""
DHH命令行工具 - 极简文件压缩

Usage:
    python dhh_cli.py compress <input> [output]
    python dhh_cli.py decompress <input> [output]
    python dhh_cli.py test <file>
"""

import sys
import os
import time
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dhh import DHHCompressor, DeltaMode


def format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def compress_file(input_path: str, output_path: str = None):
    """压缩文件"""
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    if output_path is None:
        output_path = str(input_path) + ".dhh"
    
    print(f"🗜️  压缩: {input_path.name}")
    print(f"   模式: Delta + Huffman (Simple)")
    
    compressor = DHHCompressor(DeltaMode.SIMPLE)
    
    start_time = time.time()
    stats = compressor.compress_file(str(input_path), output_path)
    elapsed = time.time() - start_time
    
    print(f"\n📊 统计:")
    print(f"   原始大小: {format_size(stats['original_size'])}")
    print(f"   压缩后:   {format_size(stats['compressed_size'])}")
    print(f"   压缩率:   {stats['savings']*100:+.1f}%")
    print(f"   速度:     {stats['original_size']/elapsed/1024/1024:.2f} MB/s")
    print(f"\n✅ 输出: {output_path}")


def decompress_file(input_path: str, output_path: str = None):
    """解压文件"""
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    if output_path is None:
        if input_path.suffix == '.dhh':
            output_path = str(input_path)[:-4]
        else:
            output_path = str(input_path) + ".out"
    
    print(f"📦 解压: {input_path.name}")
    
    compressor = DHHCompressor()
    
    start_time = time.time()
    stats = compressor.decompress_file(str(input_path), output_path)
    elapsed = time.time() - start_time
    
    print(f"\n📊 统计:")
    print(f"   压缩大小: {format_size(stats['compressed_size'])}")
    print(f"   恢复大小: {format_size(stats['decompressed_size'])}")
    print(f"   速度:     {stats['decompressed_size']/elapsed/1024/1024:.2f} MB/s")
    print(f"\n✅ 输出: {output_path}")


def test_compression(test_path: str):
    """测试压缩效果"""
    test_path = Path(test_path)
    if not test_path.exists():
        print(f"❌ 文件不存在: {test_path}")
        return
    
    print(f"🧪 测试: {test_path.name}")
    print("=" * 50)
    
    compressor = DHHCompressor()
    
    # 读取文件
    with open(test_path, 'rb') as f:
        data = f.read()
    
    # 压缩测试
    start = time.time()
    compressed = compressor.compress(data)
    compress_time = time.time() - start
    
    # 解压测试
    start = time.time()
    decompressed = compressor.decompress(compressed)
    decompress_time = time.time() - start
    
    # 验证
    match = data == decompressed
    
    print(f"原始大小:     {format_size(len(data))}")
    print(f"压缩后:       {format_size(len(compressed))}")
    print(f"压缩率:       {(1-len(compressed)/len(data))*100:+.1f}%")
    print(f"压缩时间:     {compress_time*1000:.2f} ms")
    print(f"解压时间:     {decompress_time*1000:.2f} ms")
    print(f"数据完整性:   {'✅ 通过' if match else '❌ 失败'}")
    
    # 分析Delta分布
    from dhh.delta import DeltaCodec
    deltas = DeltaCodec.encode(data)
    from collections import Counter
    freq = Counter(deltas)
    print(f"\nDelta分布 (Top 5):")
    for val, count in freq.most_common(5):
        actual = val if val <= 127 else val - 256
        print(f"   值 {actual:4d}: {count/len(deltas)*100:5.1f}%")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "compress":
        if len(sys.argv) < 3:
            print("Usage: python dhh_cli.py compress <input> [output]")
            return
        compress_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    
    elif command == "decompress":
        if len(sys.argv) < 3:
            print("Usage: python dhh_cli.py decompress <input> [output]")
            return
        decompress_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("Usage: python dhh_cli.py test <file>")
            return
        test_compression(sys.argv[2])
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
