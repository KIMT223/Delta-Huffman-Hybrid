"""
DHH核心编解码器 - Delta + Huffman Hybrid
"""
import struct
from typing import Union, Optional
from io import BytesIO

from .delta import DeltaCodec, DeltaMode
from .huffman import HuffmanCodec
from .bitstream import BitWriter, BitReader


class DHHHeader:
    """DHH文件头结构 (固定12字节)"""
    MAGIC = b'DHH\x01'
    
    __slots__ = ['version', 'mode', 'orig_size', 'sym_count']
    
    def __init__(self, mode: DeltaMode = DeltaMode.SIMPLE, 
                 orig_size: int = 0, sym_count: int = 0):
        self.version = 1
        self.mode = mode
        self.orig_size = orig_size
        self.sym_count = sym_count
    
    def pack(self) -> bytes:
        """序列化头部"""
        return struct.pack('<4sBBII', 
                          self.MAGIC, 
                          self.version,
                          self.mode.value,
                          self.orig_size,
                          self.sym_count)
    
    @classmethod
    def unpack(cls, data: bytes) -> 'DHHHeader':
        """反序列化头部"""
        if len(data) < 14:
            raise ValueError("Invalid header size")
        
        magic, version, mode_val, orig_size, sym_count = \
            struct.unpack('<4sBBII', data[:14])
        
        if magic != cls.MAGIC:
            raise ValueError(f"Invalid magic: {magic}")
        
        header = cls(DeltaMode(mode_val), orig_size, sym_count)
        header.version = version
        return header
    
    def size(self) -> int:
        return 14


class DHHCompressor:
    """
    DHH压缩器
    格式: [Header][SymbolTable][CompressedData]
    """
    
    def __init__(self, mode: DeltaMode = DeltaMode.SIMPLE):
        self.mode = mode
        self.delta_codec = DeltaCodec()
        self.huffman_codec = HuffmanCodec()
    
    def compress(self, data: bytes) -> bytes:
        """
        压缩数据
        
        Args:
            data: 原始字节数据
            
        Returns:
            压缩后的字节数据
        """
        if not data:
            return DHHHeader(self.mode, 0, 0).pack()
        
        # 1. Delta编码
        deltas = self.delta_codec.encode(data, self.mode)
        
        # 2. 构建哈夫曼树
        self.huffman_codec.build(deltas)
        self.huffman_codec.create_canonical_codes()  # 优化编码
        
        # 3. 写入头部
        sym_table = self.huffman_codec.get_symbol_table()
        header = DHHHeader(self.mode, len(data), len(sym_table))
        output = bytearray(header.pack())
        
        # 4. 写入符号表 (紧凑格式: symbol[1] + length[1] + code[2])
        for sym, length, code in sym_table:
            output.append(sym)
            output.append(length)
            output.extend(struct.pack('<H', code))
        
        # 5. 哈夫曼编码数据
        writer = BitWriter()
        for sym in deltas:
            length, code = self.huffman_codec.encode_symbol(sym)
            writer.write_bits(code, length)
        
        output.extend(writer.flush())
        return bytes(output)
    
    def decompress(self, data: bytes) -> bytes:
        """
        解压数据
        
        Args:
            data: 压缩后的数据
            
        Returns:
            原始字节数据
        """
        if len(data) < 14:
            raise ValueError("Data too short")
        
        # 1. 解析头部
        header = DHHHeader.unpack(data)
        
        if header.orig_size == 0:
            return b''
        
        # 2. 读取符号表
        pos = header.size()
        sym_table = []
        for _ in range(header.sym_count):
            if pos + 4 > len(data):
                raise ValueError("Symbol table truncated")
            sym = data[pos]
            length = data[pos + 1]
            code = struct.unpack('<H', data[pos+2:pos+4])[0]
            sym_table.append((sym, length, code))
            pos += 4
        
        # 3. 加载哈夫曼表
        self.huffman_codec.load_symbol_table(sym_table)
        
        # 4. 解码哈夫曼数据 - 使用树遍历
        reader = BitReader(data[pos:])
        deltas = []
        
        # 从哈夫曼表构建解码树
        root = {}
        for (length, code), sym in self.huffman_codec.decode_map.items():
            node = root
            for i in range(length - 1, -1, -1):  # 从高位到低位
                bit = (code >> i) & 1
                if bit not in node:
                    node[bit] = {}
                node = node[bit]
            node['sym'] = sym  # 叶子节点存储符号
        
        # 遍历比特流解码
        while len(deltas) < header.orig_size and not reader.eof():
            node = root
            while isinstance(node, dict) and 'sym' not in node and not reader.eof():
                bit = reader.read_bits(1)
                if bit in node:
                    node = node[bit]
                else:
                    raise ValueError(f"Invalid Huffman code at bit {reader.get_bits_read()}")
            
            if isinstance(node, dict) and 'sym' in node:
                deltas.append(node['sym'])
            else:
                break
        
        # 5. Delta解码
        return self.delta_codec.decode(deltas[:header.orig_size], header.mode)
    
    def compress_file(self, input_path: str, output_path: str) -> dict:
        """压缩文件并返回统计信息"""
        with open(input_path, 'rb') as f:
            data = f.read()
        
        compressed = self.compress(data)
        
        with open(output_path, 'wb') as f:
            f.write(compressed)
        
        return {
            'original_size': len(data),
            'compressed_size': len(compressed),
            'ratio': len(compressed) / len(data) if data else 0,
            'savings': 1 - len(compressed) / len(data) if data else 0
        }
    
    def decompress_file(self, input_path: str, output_path: str) -> dict:
        """解压文件并返回统计信息"""
        with open(input_path, 'rb') as f:
            data = f.read()
        
        decompressed = self.decompress(data)
        
        with open(output_path, 'wb') as f:
            f.write(decompressed)
        
        return {
            'compressed_size': len(data),
            'decompressed_size': len(decompressed)
        }
