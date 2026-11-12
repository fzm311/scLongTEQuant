#!/usr/bin/env python3
"""
Split barcodes/features/matrix files into four groups by transcript classification.

Usage:
  python split_by_transcript_classification.py \
    --barcodes barcodes.tsv \
    --features features.tsv \
    --matrix matrix.mtx \
    --quant transcript_quantification_with_TE.tsv
"""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import shutil
from dataclasses import dataclass
from typing import Dict, IO, List, Tuple


TARGET_CLASSES = ("Gene-alone", "TE-alone", "TE-Gene", "others")


@dataclass
class GroupInfo:
    name: str
    out_dir: str
    feature_path: str
    matrix_path: str
    feature_count: int = 0
    nnz_count: int = 0


def open_text(path: str, mode: str = "rt") -> IO[str]:
    if path.endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8", newline="")
    return open(path, mode, encoding="utf-8", newline="")


def read_quant_classification(quant_path: str) -> Dict[str, str]:
    classification_by_transcript: Dict[str, str] = {}

    with open_text(quant_path, "rt") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if "transcript_id" not in reader.fieldnames or "transcript_classification" not in reader.fieldnames:
            raise ValueError(
                "transcript_quantification_with_TE.tsv must include "
                "'transcript_id' and 'transcript_classification' columns."
            )
        for row in reader:
            transcript_id = (row.get("transcript_id") or "").strip()
            cls = (row.get("transcript_classification") or "").strip()
            if not transcript_id:
                continue
            if cls not in TARGET_CLASSES[:-1]:
                cls = "others"
            classification_by_transcript[transcript_id] = cls

    return classification_by_transcript


def classify_features(
    features_path: str,
    classification_by_transcript: Dict[str, str],
    groups: Dict[str, GroupInfo],
) -> Tuple[Dict[int, str], Dict[str, Dict[int, int]]]:
    """
    Returns:
      row_to_class: old 1-based row index -> class name
      row_maps: class name -> mapping old row index -> new row index
    """
    row_to_class: Dict[int, str] = {}
    row_maps: Dict[str, Dict[int, int]] = {cls: {} for cls in TARGET_CLASSES}

    feature_writers: Dict[str, IO[str]] = {}
    try:
        for cls in TARGET_CLASSES:
            feature_writers[cls] = open_text(groups[cls].feature_path, "wt")

        with open_text(features_path, "rt") as fin:
            for idx, raw_line in enumerate(fin, start=1):
                line = raw_line.rstrip("\n")
                if not line:
                    transcript_id = ""
                else:
                    transcript_id = line.split("\t", 1)[0].strip()

                cls = classification_by_transcript.get(transcript_id, "others")
                if cls not in TARGET_CLASSES:
                    cls = "others"

                row_to_class[idx] = cls
                new_idx = groups[cls].feature_count + 1
                row_maps[cls][idx] = new_idx
                groups[cls].feature_count = new_idx
                feature_writers[cls].write(raw_line)
    finally:
        for w in feature_writers.values():
            w.close()

    return row_to_class, row_maps


def read_matrix_header(fin: IO[str]) -> Tuple[List[str], str, int, int, int]:
    comments: List[str] = []
    header = fin.readline()
    if not header.startswith("%%MatrixMarket"):
        raise ValueError("Input matrix is not a valid Matrix Market file.")

    while True:
        pos_line = fin.readline()
        if not pos_line:
            raise ValueError("Matrix file ended before dimension line.")
        if pos_line.startswith("%"):
            comments.append(pos_line)
            continue
        parts = pos_line.strip().split()
        if len(parts) != 3:
            raise ValueError(f"Invalid matrix dimension line: {pos_line.strip()}")
        n_rows, n_cols, n_nnz = map(int, parts)
        return comments, header, n_rows, n_cols, n_nnz


def count_nnz_per_group(matrix_path: str, row_to_class: Dict[int, str]) -> Tuple[int, Dict[str, int]]:
    total_cols = 0
    nnz_counts = {cls: 0 for cls in TARGET_CLASSES}

    with open_text(matrix_path, "rt") as fin:
        _, _, _, n_cols, _ = read_matrix_header(fin)
        total_cols = n_cols
        for raw_line in fin:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            row = int(parts[0])
            cls = row_to_class.get(row, "others")
            if cls not in TARGET_CLASSES:
                cls = "others"
            nnz_counts[cls] += 1

    return total_cols, nnz_counts


def write_split_matrices(
    matrix_path: str,
    row_to_class: Dict[int, str],
    row_maps: Dict[str, Dict[int, int]],
    groups: Dict[str, GroupInfo],
    n_cols: int,
) -> None:
    writers: Dict[str, IO[str]] = {}
    try:
        with open_text(matrix_path, "rt") as fin:
            comments, header, _, _, _ = read_matrix_header(fin)

            for cls in TARGET_CLASSES:
                w = open_text(groups[cls].matrix_path, "wt")
                writers[cls] = w
                w.write(header)
                for c in comments:
                    w.write(c)
                w.write(f"{groups[cls].feature_count} {n_cols} {groups[cls].nnz_count}\n")

            for raw_line in fin:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                old_row = int(parts[0])
                col = parts[1]
                val = parts[2]
                cls = row_to_class.get(old_row, "others")
                if cls not in TARGET_CLASSES:
                    cls = "others"
                new_row = row_maps[cls][old_row]
                writers[cls].write(f"{new_row} {col} {val}\n")
    finally:
        for w in writers.values():
            w.close()


def build_output_groups(base_dir: str, barcodes_path: str, features_path: str, matrix_path: str) -> Dict[str, GroupInfo]:
    groups: Dict[str, GroupInfo] = {}
    barcode_name = os.path.basename(barcodes_path)
    feature_name = os.path.basename(features_path)
    matrix_name = os.path.basename(matrix_path)

    for cls in TARGET_CLASSES:
        out_dir = os.path.join(base_dir, cls)
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy2(barcodes_path, os.path.join(out_dir, barcode_name))
        groups[cls] = GroupInfo(
            name=cls,
            out_dir=out_dir,
            feature_path=os.path.join(out_dir, feature_name),
            matrix_path=os.path.join(out_dir, matrix_name),
        )
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Split barcodes/features/matrix files by transcript classification "
            "using transcript_quantification_with_TE.tsv."
        )
    )
    parser.add_argument("--barcodes", required=True, help="Path to barcodes.tsv(.gz)")
    parser.add_argument("--features", required=True, help="Path to features.tsv(.gz)")
    parser.add_argument("--matrix", required=True, help="Path to matrix.mtx(.gz)")
    parser.add_argument(
        "--quant",
        required=True,
        help="Path to transcript_quantification_with_TE.tsv(.gz)",
    )
    args = parser.parse_args()

    for p in (args.barcodes, args.features, args.matrix, args.quant):
        if not os.path.exists(p):
            raise FileNotFoundError(f"File not found: {p}")

    output_base_dir = os.path.dirname(os.path.abspath(args.matrix))
    groups = build_output_groups(output_base_dir, args.barcodes, args.features, args.matrix)

    classification_by_transcript = read_quant_classification(args.quant)
    row_to_class, row_maps = classify_features(args.features, classification_by_transcript, groups)
    n_cols, nnz_counts = count_nnz_per_group(args.matrix, row_to_class)

    for cls in TARGET_CLASSES:
        groups[cls].nnz_count = nnz_counts.get(cls, 0)

    write_split_matrices(args.matrix, row_to_class, row_maps, groups, n_cols)

    print("Finished splitting files:")
    for cls in TARGET_CLASSES:
        print(
            f"  {cls}: features={groups[cls].feature_count}, "
            f"nnz={groups[cls].nnz_count}, out_dir={groups[cls].out_dir}"
        )


if __name__ == "__main__":
    main()
