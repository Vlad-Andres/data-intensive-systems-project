#!/usr/bin/env bash

set -u

project_dir="$PWD"
data_dir="$project_dir/data"
checker="$project_dir/src/QLog_satisfaction.py"

if [[ ! -f "$checker" ]]; then
    echo "Run this script from the project root; checker not found at $checker" >&2
    exit 1
fi

shopt -s nullglob
query_logs=("$data_dir"/QLog[0-9]*_[0-9]*.txt)
if ((${#query_logs[@]} == 0)); then
    echo "No query logs found in $data_dir" >&2
    exit 1
fi

failed_logs=()
for query_log in "${query_logs[@]}"; do
    filename="${query_log##*/}"
    if [[ ! "$filename" =~ ^QLog([0-9]+)_[0-9]+\.txt$ ]]; then
        continue
    fi
    database_number="${BASH_REMATCH[1]}"

    case "$database_number" in
        1|2|3|4|5|6|7|8)
            database_name="DatabaseX_${database_number}.txt"
            ;;
        9)
            database_name="imdb_big.txt"
            ;;
        *)
            failed_logs+=("$filename (unknown database number $database_number)")
            printf '%s: FAILED (unknown database number %s)\n' "$filename" "$database_number"
            continue
            ;;
    esac
    database_path="$data_dir/$database_name"

    if ! output="$(python3 "$checker" "$database_path" "$query_log" 2>&1)"; then
        failed_logs+=("$filename ($output)")
        printf '%s (%s): FAILED\n' "$filename" "$database_name"
    else
        printf '%s (%s): %s\n' "$filename" "$database_name" "$output"
    fi
done

if ((${#failed_logs[@]} == 0)); then
    exit 0
fi

printf 'Logs that could not be checked:\n'
printf ' - %s\n' "${failed_logs[@]}"
exit 1
