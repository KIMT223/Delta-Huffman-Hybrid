"""
DHH (Delta-Huffman Hybrid) Compression Library
"""

from setuptools import setup, find_packages
from pathlib import Path
import os

# 读取README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ""

# 确保脚本有执行权限
script_path = Path(__file__).parent / "tools" / "dhh_cli.py"
if script_path.exists():
    os.chmod(script_path, 0o755)

setup(
    name="dhh-compression",
    version="1.0.0",
    author="DHH Team",
    author_email="dhh@example.com",
    description="Delta-Huffman Hybrid Compression - 极简高效的文件压缩算法",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dhh",
    
    packages=find_packages(exclude=["tests", "tests.*"]),
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Archiving :: Compression",
    ],
    
    python_requires=">=3.7",
    install_requires=[],
    
    # 关键：安装脚本到 bin 目录
    scripts=['tools/dhh_cli.py'],
    
    include_package_data=True,
    zip_safe=False,
)
