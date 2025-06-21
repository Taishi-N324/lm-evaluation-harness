#!/bin/bash
#PBS -P gcg51557
#PBS -q R9920251000
#PBS -N 0134_eval
#PBS -v RTYPE=rt_HF
#PBS -l select=1:ngpus=1:ncpus=8
#PBS -l walltime=168:00:00
#PBS -j oe
#PBS -koed
#PBS -V
#PBS -o outputs/
#PBS -m n

set -eu -o pipefail

cd $PBS_O_WORKDIR

export CUDA_VISIBLE_DEVICES=0
source .venv/bin/activate

ARITH_TASKS="arithmetic"
ARITH_OUTDIR="results/${MODEL_NAME_PATH}/en/harness_en/alltasks_${ARITH_NUM_FEWSHOT}shot/arithmetic"

mkdir -p "$ARITH_OUTDIR"

lm_eval --model vllm \
    --model_args pretrained=$MODEL_NAME_PATH,max_length=4096,tensor_parallel_size=$TP,dtype=auto,gpu_memory_utilization=0.7,data_parallel_size=$DP \
    --tasks $ARITH_TASKS \
    --num_fewshot $ARITH_NUM_FEWSHOT \
    --batch_size auto \
    --device cuda \
    --write_out \
    --output_path "$ARITH_OUTDIR" \
    --use_cache "$ARITH_OUTDIR" \
    --log_samples \
    --seed 42

python scripts/aggregate_result.py --model $MODEL_NAME_PATH
