"""
紧凑的比特流读写器，支持按位操作
"""
from typing import List, Tuple
from io import BytesIO


class BitWriter:
    """比特流写入器"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.current_byte = 0
        self.bit_pos = 0  # 0-7，当前字节中的位位置
    
    def write_bits(self, value: int, num_bits: int) -> None:
        """写入指定数量的比特（高位优先）"""
        for i in range(num_bits - 1, -1, -1):
            bit = (value >> i) & 1
            self.current_byte = (self.current_byte << 1) | bit
            self.bit_pos += 1
            
            if self.bit_pos == 8:
                self.buffer.append(self.current_byte)
                self.current_byte = 0
                self.bit_pos = 0
    
    def flush(self) -> bytes:
        """刷新并返回字节流，填充剩余位"""
        if self.bit_pos > 0:
            self.current_byte <<= (8 - self.bit_pos)
            self.buffer.append(self.current_byte)
            self.current_byte = 0
            self.bit_pos = 0
        return bytes(self.buffer)
    
    def get_bits_written(self) -> int:
        """返回已写入的总比特数"""
        return len(self.buffer) * 8 + self.bit_pos


class BitReader:
    """比特流读取器"""
    
    def __init__(self, data: bytes):
        self.data = data
        self.byte_pos = 0
        self.bit_pos = 0  # 0-7，当前字节中的位位置
    
    def read_bits(self, num_bits: int) -> int:
        """读取指定数量的比特（高位优先）"""
        result = 0
        for _ in range(num_bits):
            if self.byte_pos >= len(self.data):
                raise EOFError("Unexpected end of bitstream")
            
            byte = self.data[self.byte_pos]
            bit = (byte >> (7 - self.bit_pos)) & 1
            
            result = (result << 1) | bit
            self.bit_pos += 1
            
            if self.bit_pos == 8:
                self.bit_pos = 0
                self.byte_pos += 1
        
        return result
    
    def read_byte(self) -> int:
        """读取完整字节（快捷方式）"""
        return self.read_bits(8)
    
    def eof(self) -> bool:
        """检查是否已读完"""
        return self.byte_pos >= len(self.data)
    
    def get_bits_read(self) -> int:
        """返回已读取的总比特数"""
        return self.byte_pos * 8 + self.bit_pos
