#!/bash/bin
lang=$1
model_path=$2
echo $lang
echo $model_path

ybatch scripts/ylab/gpt_bigcode/run_arc.sh $lang $model_path
ybatch scripts/ylab/gpt_bigcode/run_hellaswag.sh $lang $model_path
ybatch scripts/ylab/gpt_bigcode/run_mmlu.sh $lang $model_path
ybatch scripts/ylab/gpt_bigcode/run_truthfulqa.sh $lang $model_path