#!/bin/bash
#YBATCH -r a6000_1
#SBATCH --nodes 1
#SBATCH -J arc_mlmm
#SBATCH --time=168:00:00
#SBATCH --output outputs/%j.out
#SBATCH --error errors/%j.err

. /etc/profile.d/modules.sh
module load cuda/11.7
module load cudnn/cuda-11.x/8.9.0
module load nccl/cuda-11.7/2.14.3
module load openmpi/4.0.5

export HF_HOME=/home/tn/.cache
export HF_DATASETS_CACHE=/home/tn/.cache
export TRANSFORMERS_CACHE=/home/tn/.cache



lang=$1
model_path=$2
model_id=$(basename $model_path) 
tasks=arc_${lang}
device=cuda
output_dir="results/${model_path}/_model_id_${lang}_lang_${tasks}_tasks.json" 
 
python main.py \
    --tasks=${tasks} \
    --batch_size 1 \
    --model_alias llama \
    --task_alias open_llm \
    --model_args pretrained=$model_path,trust_remote_code=True,use_accelerate=True,dtype="bfloat16" \
    --device=${device} \
    --output_path=${output_dir} \
   
    # --write_out
