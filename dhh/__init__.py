"""
Delta-Huffman Hybrid (DHH) Compression Library

极简高效的文件压缩算法，结合Delta编码和Huffman编码优势。
"""

__version__ = "1.0.0"
__author__ = "DHH Team"

from .core import DHHCompressor, DHHHeader
from .delta import DeltaCodec, DeltaMode
from .huffman import HuffmanCodec

__all__ = [
    'DHHCompressor',
    'DHHHeader', 
    'DeltaCodec',
    'DeltaMode',
    'HuffmanCodec'
]
