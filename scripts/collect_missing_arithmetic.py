#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_missing_arithmetic.py

show_result.py で生成された CSV を読み込み、
Arithmetic (0-shot & 1-shot & 5-shot) が未評価 (-1.0) のモデルに対して
qsub コマンドを生成する。

Usage:
  python collect_missing_arithmetic.py --csv results.csv \
                                       --out missing_jobs_arith.sh \
                                       [--queue]  # 付けると即投入
"""
from __future__ import annotations
import argparse, csv, subprocess, sys
from pathlib import Path

# ------------------------------------------------------------
ARITH_COLUMNS = {
    0: [  # 0-shot
        "arithmetic_1dc_0shot",
        "arithmetic_2da_0shot",
        "arithmetic_2dm_0shot",
        "arithmetic_2ds_0shot",
        "arithmetic_3da_0shot",
        "arithmetic_3ds_0shot",
        "arithmetic_4da_0shot",
        "arithmetic_4ds_0shot",
        "arithmetic_5da_0shot",
        "arithmetic_5ds_0shot",
    ],
    1: [  # 1-shot
        "arithmetic_1dc_1shot",
        "arithmetic_2da_1shot",
        "arithmetic_2dm_1shot",
        "arithmetic_2ds_1shot",
        "arithmetic_3da_1shot",
        "arithmetic_3ds_1shot",
        "arithmetic_4da_1shot",
        "arithmetic_4ds_1shot",
        "arithmetic_5da_1shot",
        "arithmetic_5ds_1shot",
    ],
    5: [  # 5-shot
        "arithmetic_1dc_5shot",
        "arithmetic_2da_5shot",
        "arithmetic_2dm_5shot",
        "arithmetic_2ds_5shot",
        "arithmetic_3da_5shot",
        "arithmetic_3ds_5shot",
        "arithmetic_4da_5shot",
        "arithmetic_4ds_5shot",
        "arithmetic_5da_5shot",
        "arithmetic_5ds_5shot",
    ],
}


# ------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="show_result.py で生成された CSV ファイル",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default="scripts/missing_arithmetic_jobs.sh",
        help="qsub コマンドを書き出すシェルスクリプト",
    )
    ap.add_argument("--queue", action="store_true", help="即座に qsub を実行する")
    args = ap.parse_args()

    # --------------------------------------------------------
    # CSV 読み込み ⇒ <model, missing_shots(set)>
    missing: dict[str, set[int]] = {}

    with args.csv.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row.get("model") or row.get("model_name") or row.get("model_path")
            if model is None:
                print("⚠️  'model' 列が見つかりませんでした。", file=sys.stderr)
                sys.exit(1)

            for shot, cols in ARITH_COLUMNS.items():
                if any(float(row.get(c, "0")) == -1.0 for c in cols):
                    missing.setdefault(model, set()).add(shot)

    # --------------------------------------------------------
    if not missing:
        print("✓ すべてのモデルで Arithmetic 評価が完了しています。")
        return

    print(f"⚠️  {sum(len(s) for s in missing.values())} 件の未評価タスクがあります。")

    # --------------------------------------------------------
    # qsub コマンド生成
    cmds: list[str] = []
    for model, shots in missing.items():
        for shot in sorted(shots):  # 0, 1, 5 の順
            # 大型モデル (52B) だけ設定を変える例
            if "52b" in model.lower():
                rtype, tp = "rt_HF", 4
            else:
                rtype, tp = "rt_HG", 1

            cmd = (
                f"qsub -v RTYPE={rtype},MODEL_NAME_PATH={model},"
                f"TP={tp},DP=1,ARITH_NUM_FEWSHOT={shot} "
                "scripts/abci3/rt_HF/arithmetic.sh"
            )
            cmds.append(cmd)
            print(f"  - {model} (shot={shot})")

    # --------------------------------------------------------
    if args.queue:
        print("\n▶ qsub コマンドを実行します...")
        for cmd in cmds:
            print(f" $ {cmd}")
            subprocess.run(cmd, shell=True, check=False)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "#!/bin/bash\n\n"
            "# Missing Arithmetic evaluation jobs\n"
            f"# Generated from: {args.csv}\n"
            f"# Total commands: {len(cmds)}\n\n"
        )
        args.out.write_text(header + "\n".join(cmds) + "\n")
        args.out.chmod(0o755)
        print(f"\n✓ qsub コマンドを {args.out} に書き出しました。")
        print(f"   実行するには: ./{args.out} あるいは bash {args.out}")


# ------------------------------------------------------------
if __name__ == "__main__":
    main()
