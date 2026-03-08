"""
DHH文件操作模块 - 支持大文件分块处理
"""
import os
from pathlib import Path
from typing import Union, Iterator, Callable, Optional
from .core import DHHCompressor, DHHHeader


class ChunkedFileReader:
    """分块文件读取器，支持大文件"""
    
    def __init__(self, path: Union[str, Path], chunk_size: int = 64 * 1024):
        self.path = Path(path)
        self.chunk_size = chunk_size
        self._size = self.path.stat().st_size
    
    def __iter__(self) -> Iterator[bytes]:
        """迭代器产生数据块"""
        with open(self.path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
    
    def read_all(self) -> bytes:
        """读取全部内容（小文件用）"""
        with open(self.path, 'rb') as f:
            return f.read()
    
    @property
    def size(self) -> int:
        return self._size


class DHHFileHandler:
    """
    DHH文件处理器
    支持：单文件压缩/解压、批量处理、进度回调
    """
    
    # 大文件阈值：超过此大小使用流式处理
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, compressor: Optional[DHHCompressor] = None):
        self.compressor = compressor or DHHCompressor()
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        设置进度回调函数
        callback(current, total, status)
        """
        self._progress_callback = callback
    
    def _notify(self, current: int, total: int, status: str):
        """触发进度通知"""
        if self._progress_callback:
            self._progress_callback(current, total, status)
    
    def compress_file(self, input_path: Union[str, Path], 
                     output_path: Union[str, Path],
                     use_streaming: bool = False) -> dict:
        """
        压缩单个文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            use_streaming: 是否使用流式处理（大文件）
        
        Returns:
            统计信息字典
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        file_size = input_path.stat().st_size
        
        # 小文件直接内存处理
        if not use_streaming and file_size < self.LARGE_FILE_THRESHOLD:
            return self._compress_small_file(input_path, output_path)
        
        # 大文件流式处理
        return self._compress_large_file(input_path, output_path)
    
    def _compress_small_file(self, input_path: Path, output_path: Path) -> dict:
        """压缩小文件（内存模式）"""
        self._notify(0, 100, "Reading...")
        
        with open(input_path, 'rb') as f:
            data = f.read()
        
        self._notify(30, 100, "Compressing...")
        compressed = self.compressor.compress(data)
        
        self._notify(80, 100, "Writing...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(compressed)
        
        self._notify(100, 100, "Done")
        
        return {
            'mode': 'memory',
            'original_size': len(data),
            'compressed_size': len(compressed),
            'ratio': len(compressed) / len(data) if data else 0,
            'savings': 1 - len(compressed) / len(data) if data else 0,
            'input_path': str(input_path),
            'output_path': str(output_path)
        }
    
    def _compress_large_file(self, input_path: Path, output_path: Path) -> dict:
        """
        压缩大文件（分块流式模式）
        格式: [GlobalHeader][Block1Header][Block1Data][Block2...]
        """
        block_size = 1024 * 1024  # 1MB per block
        total_size = input_path.stat().st_size
        processed = 0
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            # 写入流式文件头标记
            fout.write(b'DHH\x02')  # 版本2：流式格式
            fout.write(total_size.to_bytes(8, 'little'))  # 8字节原始大小
            
            block_count = 0
            total_compressed = 4 + 8  # 头部大小
            
            while True:
                chunk = fin.read(block_size)
                if not chunk:
                    break
                
                self._notify(processed, total_size, f"Compressing block {block_count+1}")
                
                # 压缩块
                compressed_block = self.compressor.compress(chunk)
                
                # 写入块大小（4字节）+ 压缩数据
                fout.write(len(compressed_block).to_bytes(4, 'little'))
                fout.write(compressed_block)
                
                total_compressed += 4 + len(compressed_block)
                processed += len(chunk)
                block_count += 1
            
            self._notify(total_size, total_size, "Done")
            
            return {
                'mode': 'streaming',
                'original_size': total_size,
                'compressed_size': total_compressed,
                'ratio': total_compressed / total_size if total_size else 0,
                'savings': 1 - total_compressed / total_size if total_size else 0,
                'blocks': block_count,
                'input_path': str(input_path),
                'output_path': str(output_path)
            }
    
    def decompress_file(self, input_path: Union[str, Path],
                       output_path: Union[str, Path]) -> dict:
        """
        解压文件（自动检测格式）
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # 检测格式
        with open(input_path, 'rb') as f:
            magic = f.read(4)
        
        if magic == b'DHH\x01':
            return self._decompress_small_file(input_path, output_path)
        elif magic == b'DHH\x02':
            return self._decompress_large_file(input_path, output_path)
        else:
            raise ValueError(f"Unknown file format: {magic}")
    
    def _decompress_small_file(self, input_path: Path, output_path: Path) -> dict:
        """解压标准格式文件"""
        self._notify(0, 100, "Reading...")
        
        with open(input_path, 'rb') as f:
            data = f.read()
        
        self._notify(40, 100, "Decompressing...")
        decompressed = self.compressor.decompress(data)
        
        self._notify(80, 100, "Writing...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(decompressed)
        
        self._notify(100, 100, "Done")
        
        return {
            'mode': 'memory',
            'compressed_size': len(data),
            'decompressed_size': len(decompressed),
            'input_path': str(input_path),
            'output_path': str(output_path)
        }
    
    def _decompress_large_file(self, input_path: Path, output_path: Path) -> dict:
        """解压流式格式文件"""
        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            # 读取头部
            magic = fin.read(4)
            total_size = int.from_bytes(fin.read(8), 'little')
            
            processed = 0
            block_num = 0
            
            while processed < total_size:
                self._notify(processed, total_size, f"Decompressing block {block_num+1}")
                
                # 读取块大小
                block_size_data = fin.read(4)
                if not block_size_data:
                    break
                
                block_size = int.from_bytes(block_size_data, 'little')
                compressed_block = fin.read(block_size)
                
                # 解压块
                decompressed = self.compressor.decompress(compressed_block)
                fout.write(decompressed)
                
                processed += len(decompressed)
                block_num += 1
            
            self._notify(total_size, total_size, "Done")
            
            return {
                'mode': 'streaming',
                'blocks': block_num,
                'decompressed_size': processed,
                'input_path': str(input_path),
                'output_path': str(output_path)
            }
    
    def batch_compress(self, input_paths: list, output_dir: Union[str, Path],
                      pattern: str = "{}.dhh") -> list:
        """
        批量压缩文件
        
        Args:
            input_paths: 输入文件路径列表
            output_dir: 输出目录
            pattern: 输出文件名模式，{}替换为原文件名
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        total = len(input_paths)
        
        for i, path in enumerate(input_paths):
            path = Path(path)
            if not path.exists():
                results.append({'input': str(path), 'error': 'Not found'})
                continue
            
            output_name = pattern.format(path.stem)
            output_path = output_dir / output_name
            
            try:
                self._notify(i, total, f"Compressing {path.name}")
                result = self.compress_file(path, output_path)
                results.append(result)
            except Exception as e:
                results.append({'input': str(path), 'error': str(e)})
        
        return results


def get_file_type(path: Union[str, Path]) -> str:
    """简单检测文件类型"""
    path = Path(path)
    
    # 读取文件头
    try:
        with open(path, 'rb') as f:
            header = f.read(16)
    except:
        return "unknown"
    
    # 检测DHH格式
    if header[:4] == b'DHH\x01':
        return "dhh/standard"
    if header[:4] == b'DHH\x02':
        return "dhh/streaming"
    
    # 常见格式检测
    magic_map = {
        b'\x89PNG': "image/png",
        b'\xff\xd8\xff': "image/jpeg",
        b'PK\x03\x04': "application/zip",
        b'Rar!': "application/x-rar",
        b'GIF8': "image/gif",
        b'%PDF': "application/pdf",
        b'\x1f\x8b': "application/gzip",
        b'BZ': "application/x-bzip2",
        b'\xfd7zXZ': "application/x-xz",
    }
    
    for magic, ftype in magic_map.items():
        if header.startswith(magic):
            return ftype
    
    # 文本检测
    try:
        header.decode('utf-8')
        return "text/plain"
    except:
        return "application/octet-stream"
