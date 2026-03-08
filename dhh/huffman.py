"""
极简哈夫曼编码实现，使用堆优化
"""
import heapq
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional


class HuffmanNode:
    """哈夫曼树节点"""
    __slots__ = ['weight', 'symbol', 'left', 'right', 'is_leaf']
    
    def __init__(self, weight: int, symbol: Optional[int] = None):
        self.weight = weight
        self.symbol = symbol
        self.left: Optional['HuffmanNode'] = None
        self.right: Optional['HuffmanNode'] = None
        self.is_leaf = symbol is not None
    
    def __lt__(self, other: 'HuffmanNode') -> bool:
        return self.weight < other.weight


class HuffmanCodec:
    """哈夫曼编解码器"""
    
    def __init__(self):
        self.codes: Dict[int, Tuple[int, int]] = {}  # symbol -> (length, code)
        self.tree: Optional[HuffmanNode] = None
        self.decode_map: Dict[Tuple[int, int], int] = {}  # (length, code) -> symbol
    
    def build(self, data: List[int]) -> None:
        """从数据构建哈夫曼树"""
        if not data:
            return
        
        freq = Counter(data)
        
        # 单符号特殊情况
        if len(freq) == 1:
            sym = list(freq.keys())[0]
            self.codes = {sym: (1, 0)}
            self._build_decode_map()
            return
        
        # 构建最小堆
        heap = [HuffmanNode(w, s) for s, w in freq.items()]
        heapq.heapify(heap)
        
        # 合并节点
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(left.weight + right.weight)
            parent.left = left
            parent.right = right
            heapq.heappush(heap, parent)
        
        self.tree = heap[0]
        self.codes = {}
        self._generate_codes(self.tree, 0, 0)
        self._build_decode_map()
    
    def _generate_codes(self, node: HuffmanNode, code: int, depth: int) -> None:
        """递归生成编码"""
        if node.is_leaf:
            # 处理单节点情况（深度为0）
            if depth == 0:
                self.codes[node.symbol] = (1, 0)
            else:
                self.codes[node.symbol] = (depth, code)
            return
        
        if node.left:
            self._generate_codes(node.left, code << 1, depth + 1)
        if node.right:
            self._generate_codes(node.right, (code << 1) | 1, depth + 1)
    
    def _build_decode_map(self) -> None:
        """构建解码映射表（用于快速查找）"""
        self.decode_map = {(length, code): sym for sym, (length, code) in self.codes.items()}
    
    def encode_symbol(self, symbol: int) -> Tuple[int, int]:
        """获取符号的编码（长度，编码值）"""
        return self.codes.get(symbol, (8, symbol))  # 回退到定长编码
    
    def get_symbol_table(self) -> List[Tuple[int, int, int]]:
        """获取符号表用于序列化 [(symbol, length, code), ...]"""
        return [(sym, length, code) for sym, (length, code) in self.codes.items()]
    
    def load_symbol_table(self, table: List[Tuple[int, int, int]]) -> None:
        """从序列化数据加载符号表"""
        self.codes = {sym: (length, code) for sym, length, code in table}
        self._build_decode_map()
    
    def create_canonical_codes(self) -> None:
        """转换为规范哈夫曼编码（更紧凑的存储）"""
        # 按符号值排序，相同长度按编码排序
        items = sorted(self.codes.items(), key=lambda x: (x[1][0], x[0]))
        
        new_codes = {}
        code = 0
        prev_length = 0
        
        for sym, (length, _) in items:
            if length > prev_length:
                code <<= (length - prev_length)
                prev_length = length
            new_codes[sym] = (length, code)
            code += 1
        
        self.codes = new_codes
        self._build_decode_map()
