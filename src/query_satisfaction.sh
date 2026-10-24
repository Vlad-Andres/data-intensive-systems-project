#!/usr/bin/env bash

set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
data_dir="$project_dir/data"
checker="$script_dir/query_satisfaction.py"

shopt -s nullglob
query_logs=("$data_dir"/QLog[0-9]*_DB_[0-9]*.txt)
if ((${#query_logs[@]} == 0)); then
    echo "No query logs found in $data_dir" >&2
    exit 1
fi

failed_logs=()
total_logs=${#query_logs[@]}
checked_logs=0
for query_log in "${query_logs[@]}"; do
    filename="${query_log##*/}"
    if [[ ! "$filename" =~ ^QLog([0-9]+)_DB_[0-9]+\.txt$ ]]; then
        continue
    fi
    ((checked_logs += 1))
    database_number="${BASH_REMATCH[1]}"

    printf '\r\033[K[%d/%d] Checking %s ...' "$checked_logs" "$total_logs" "$filename"
    case "$database_number" in
        1|2|3|4|5|6|7|8)
            database_path="$data_dir/DatabaseX_${database_number}.txt"
            ;;
        9)
            database_path="$data_dir/imdb_big.txt"
            ;;
        *)
            printf '\r\033[K[%d/%d] %s: FAILED' "$checked_logs" "$total_logs" "$filename"
            failed_logs+=("$filename (unknown database number $database_number)")
            continue
            ;;
    esac

    if ! output="$(python3 "$checker" "$database_path" "$query_log" 2>&1)"; then
        printf '\r\033[K[%d/%d] %s: FAILED' "$checked_logs" "$total_logs" "$filename"
        failed_logs+=("$filename")
    else
        printf '\r\033[K[%d/%d] %s: OK' "$checked_logs" "$total_logs" "$filename"
    fi
done

printf '\n'
if ((${#failed_logs[@]} == 0)); then
    echo "👌 All Satisfied"
    exit 0
fi

printf 'Non-satisfied logs:\n'
printf ' - %s\n' "${failed_logs[@]}"
exit 1
