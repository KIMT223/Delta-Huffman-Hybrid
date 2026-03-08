"""
Delta编解码模块，支持多种预测模式
"""
from typing import List
from enum import Enum


class DeltaMode(Enum):
    """Delta预测模式"""
    SIMPLE = 0      # 简单差分: d[i] = data[i] - data[i-1]
    DOUBLE = 1      # 二阶差分: d2[i] = d[i] - d[i-1]


class DeltaCodec:
    """Delta编解码器"""
    
    @staticmethod
    def encode(data: bytes, mode: DeltaMode = DeltaMode.SIMPLE) -> List[int]:
        """
        Delta编码
        返回: [首字节, 差分1, 差分2, ...] 所有值映射到0-255
        """
        if not data:
            return []
        
        if len(data) == 1:
            return [data[0]]
        
        deltas = [data[0]]  # 首字节原样存储
        
        if mode == DeltaMode.SIMPLE:
            for i in range(1, len(data)):
                diff = data[i] - data[i-1]
                # 有符号转无符号: -128~127 → 0~255
                deltas.append((diff + 256) % 256)
                
        elif mode == DeltaMode.DOUBLE:
            # 二阶差分：适合平滑数据
            if len(data) >= 2:
                first_diff = data[1] - data[0]
                deltas.append((first_diff + 256) % 256)
                
                prev_diff = first_diff
                for i in range(2, len(data)):
                    curr_diff = data[i] - data[i-1]
                    diff2 = curr_diff - prev_diff
                    deltas.append((diff2 + 256) % 256)
                    prev_diff = curr_diff
        
        return deltas
    
    @staticmethod
    def decode(deltas: List[int], mode: DeltaMode = DeltaMode.SIMPLE) -> bytes:
        """Delta解码"""
        if not deltas:
            return b''
        
        if len(deltas) == 1:
            return bytes([deltas[0]])
        
        result = bytearray()
        result.append(deltas[0])
        
        if mode == DeltaMode.SIMPLE:
            for i in range(1, len(deltas)):
                diff = deltas[i]
                if diff > 127:  # 无符号转有符号
                    diff -= 256
                result.append((result[-1] + diff) % 256)
                
        elif mode == DeltaMode.DOUBLE:
            # 二阶解码
            first_diff = deltas[1]
            if first_diff > 127:
                first_diff -= 256
            result.append((result[-1] + first_diff) % 256)
            
            prev_diff = first_diff
            for i in range(2, len(deltas)):
                diff2 = deltas[i]
                if diff2 > 127:
                    diff2 -= 256
                curr_diff = (prev_diff + diff2) % 256
                if curr_diff > 127:
                    curr_diff -= 256
                result.append((result[-1] + curr_diff) % 256)
                prev_diff = curr_diff
        
        return bytes(result)
