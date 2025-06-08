#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_missing_humaneval_mbpp.py

show_result.py で生成されたCSVを読み込み、
-1.0 の値を持つモデルに対して qsub コマンドを生成する

Usage:
  python collect_missing_humaneval_mbpp.py --csv results.csv \
                                          --out missing_jobs.sh \
                                          [--queue]  # 付けると即投入
"""

from __future__ import annotations
import argparse
import csv
import subprocess
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv", type=Path, required=True, help="show_result.py で生成されたCSVファイル"
    )
    ap.add_argument(
        "--out",
        type=Path,
        default="scripts/missing_humaneval_mbpp_jobs.sh",
        help="qsubコマンドを書き出すシェルスクリプト",
    )
    ap.add_argument("--queue", action="store_true", help="即座にqsubを実行する")
    args = ap.parse_args()

    # CSVを読み込む
    missing_models = []

    with args.csv.open("r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model_path = row["model"]

            # いずれかのスコアが -1.0 の場合、未実行と判断
            has_missing = any(
                float(row.get(col, 0)) == -1.0
                for col in [
                    "humaneval_0shot",
                    "humaneval_plus_0shot",
                    "mbpp_3shot",
                    "mbpp_plus_3shot",
                ]
                if col in row
            )

            if has_missing:
                missing_models.append(model_path)

    if not missing_models:
        print("✓ すべてのモデルで評価が完了しています。")
        return

    print(f"⚠️  {len(missing_models)} 個のモデルで未評価のタスクがあります。")

    # qsubコマンドを生成
    qsub_commands = []
    for model_path in missing_models:
        # 52bモデルの場合はTP=4, RTYPE=rt_HF
        if "52b" in model_path.lower():
            cmd = f"qsub -v RTYPE=rt_HF,MODEL_NAME_PATH={model_path},TP=4,DP=1 scripts/abci3/rt_HF/humaneval_mbpp.sh"
        else:
            cmd = f"qsub -v RTYPE=rt_HG,MODEL_NAME_PATH={model_path},TP=1,DP=1 scripts/abci3/rt_HF/humaneval_mbpp.sh"
        qsub_commands.append(cmd)
        print(f"  - {model_path}")

    if args.queue:
        # 即座に実行
        print("\n▶ qsub コマンドを実行します...")
        for cmd in qsub_commands:
            print(f" $ {cmd}")
            try:
                res = subprocess.run(cmd, shell=True, check=False)
                if res.returncode != 0:
                    print(f"  ⚠️  failed (exit {res.returncode})", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  error: {e}", file=sys.stderr)
    else:
        # シェルスクリプトに書き出し
        args.out.parent.mkdir(parents=True, exist_ok=True)

        script_content = "#!/bin/bash\n\n"
        script_content += "# Missing HumanEval/MBPP evaluation jobs\n"
        script_content += f"# Generated from: {args.csv}\n"
        script_content += f"# Total models: {len(missing_models)}\n"
        script_content += "# Note: 52b models use TP=4 and RTYPE=rt_HF\n\n"

        for cmd in qsub_commands:
            script_content += cmd + "\n"

        args.out.write_text(script_content)
        args.out.chmod(0o755)

        print(f"\n✓ qsub コマンドを {args.out} に書き出しました。")
        print(f"   実行するには: ./{args.out} または bash {args.out}")


if __name__ == "__main__":
    main()
