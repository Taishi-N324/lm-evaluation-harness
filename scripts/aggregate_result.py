import argparse
import json
import os
from datetime import datetime
from functools import reduce
from operator import getitem
from typing import Any, Dict, List, Tuple
from pathlib import Path

import pandas as pd

SUBTASKS_COLUMNS_MAP = {
    "MC": ["jcommonsenseqa"],
    "NLI": ["jamp (NLI)", "janli (NLI)", "jnli", "jsem", "jsick (NLI)"],
    "QA": ["jemhopqa", "niilc"],
    "RC": ["jsquad"],
}


def load_json(input_path: str) -> Dict[str, Any]:
    with open(input_path, "r") as file:
        data = json.load(file)
    return data


def get_nested_dict_value(input_path: str, keys: List[str]) -> float:
    d = load_json(input_path)
    try:
        metric = float(reduce(getitem, keys, d))
    except KeyError:
        print(f"Key not found: {keys}")
        return -1.0
    return metric


def get_average_score(input_path: str, keys: List[str]) -> float:
    """get average score from multiple keys"""
    scores = [get_nested_dict_value(input_path, key) for key in keys]
    if -1.0 in scores:
        return -1.0
    return sum(scores) / len(scores)


def find_all_result_files(directory: str, model: str) -> List[Tuple[str, datetime]]:
    """
    Find all results_*.json files in the given directory and return them sorted by date
    Returns list of tuples (file_path, modification_time)
    """
    model_variants = [
        f"__{model.replace('/', '__')}__",
        f"__{model.replace('/', '__')}",
        f"{model.replace('/', '__')}__",
        f"{model.replace('/', '__')}",
    ]

    result_files = []
    parent_dir = os.path.dirname(directory)
    for root, dirs, files in os.walk(parent_dir):
        for f in files:
            if f.startswith("results_") and f.endswith(".json"):
                file_path = os.path.join(root, f)
                print("file_path", file_path)
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                result_files.append((file_path, mod_time))

    if not result_files:
        raise FileNotFoundError(
            f"No results file found for model {model} in {directory}"
        )

    # Sort by modification time, newest first
    return sorted(result_files, key=lambda x: x[1], reverse=True)


def get_best_metric(result_files: List[Tuple[str, datetime]], keys: List[str]) -> float:
    """
    Get the best metric from all result files, prioritizing the newest files
    """
    for file_path, _ in result_files:
        try:
            metric = get_nested_dict_value(file_path, keys)
            if metric != -1.0:
                return metric
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            continue
    return -1.0


def get_best_average_score(
    result_files: List[Tuple[str, datetime]], keys: List[str]
) -> float:
    """
    Get the best average score from all result files, prioritizing the newest files
    """
    for file_path, _ in result_files:
        try:
            score = get_average_score(file_path, keys)
            if score != -1.0:
                return score
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            continue
    return -1.0


def aggregate_results(model: str) -> Dict[str, float]:
    """load all results of the model and aggregate the scores into a single dictionary"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    column_path_key_csv = pd.read_csv(os.path.join(script_dir, "column-path-key.csv"))
    task_keys_map = {
        k: [key.replace("MODEL_NAME", model.replace("/", "_")) for key in v.split(".")]
        for k, v in column_path_key_csv[["column", "key"]].values
    }

    results = {}
    overall = []
    model_path = Path(model)
    if model_path.is_absolute():
        model_path = Path(*model_path.parts[1:])

    result_root_dir = Path.cwd() / "results" / model_path

    for _, row in column_path_key_csv.iterrows():
        column, path, _, max_score = row
        keys = task_keys_map[column]

        try:
            result_dir = os.path.join(result_root_dir, path)
            result_files = find_all_result_files(result_dir, model)

            if column in SUBTASKS_COLUMNS_MAP.keys():
                subtasks = SUBTASKS_COLUMNS_MAP[column]
                keys_subtasks = [task_keys_map[subtask] for subtask in subtasks]
                metric = get_best_average_score(result_files, keys_subtasks)
            else:
                metric = get_best_metric(result_files, keys)

            metric = metric / float(max_score)

        except (FileNotFoundError, Exception) as e:
            print(f"Error processing {column}: {str(e)}")
            metric = -1.0

        results[column] = metric
        overall.append(metric)

    json_result = {
        "model": model,
        "result": results,
        "overall": ",".join(map(str, overall)),
        "tasks": list(results.keys()),
    }

    os.makedirs(
        os.path.dirname(f"{result_root_dir}/aggregated_result.json"), exist_ok=True
    )
    json.dump(
        json_result,
        open(f"{result_root_dir}/aggregated_result.json", "w"),
        indent=2,
        ensure_ascii=False,
    )

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", required=True, type=str, help="Model name to aggregate"
    )
    args = parser.parse_args()
    aggregate_results(args.model)


if __name__ == "__main__":
    main()
