#!/usr/bin/env python3
"""
仅转置 matrix.mtx，不修改 barcodes.tsv 和 features.tsv。
适用于：barcodes/features 标签顺序正确，但矩阵行/列方向反了的情况。
用法: python fix_matrix_transpose.py <输入目录> <输出目录>
"""

import os
import sys
import shutil
from scipy.io import mmread, mmwrite
from scipy.sparse import csr_matrix

def main():
    if len(sys.argv) != 3:
        print("用法: python fix_matrix_transpose.py <输入目录> <输出目录>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # 1. 原样复制 barcodes 和 features（因为它们是对的）
    for fname in ['barcodes.tsv', 'features.tsv']:
        src = os.path.join(input_dir, fname)
        dst = os.path.join(output_dir, fname)
        if not os.path.isfile(src):
            sys.exit(f"错误：找不到 {src}")
        os.makedirs(output_dir, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"已复制 {fname} (内容不变)")

    # 2. 读取并转置矩阵
    matrix_path = os.path.join(input_dir, 'matrix.mtx')
    if not os.path.isfile(matrix_path):
        sys.exit(f"错误：找不到 {matrix_path}")

    mat = mmread(matrix_path).tocsr()
    print(f"原始矩阵维度: {mat.shape}")

    # 执行转置（行和列互换）
    mat_T = mat.T.tocsr()
    print(f"转置后矩阵维度: {mat_T.shape}")

    # 3. 写入新的 matrix.mtx
    out_matrix = os.path.join(output_dir, 'matrix.mtx')
    mmwrite(out_matrix, mat_T)
    print(f"转置后的矩阵已保存至: {out_matrix}")

if __name__ == '__main__':
    main()
