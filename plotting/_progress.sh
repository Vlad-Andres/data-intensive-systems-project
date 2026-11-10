# Sourced by the plotting scripts: a one-line progress bar and a runner that logs main.py output.
# Before the loop set: total=<number of runs>, LOG=<log file>; then call run_main "<label>" <main.py arguments...> per run.

finished=0
start=$(date +%s)

progress() {  # [#####     ] runs done / total, estimated minutes left, current run
    local width=30 filled=$(( finished * 30 / total )) left="?"
    [ "$finished" -gt 0 ] && left="$(( ($(date +%s) - start) * (total - finished) / finished / 60 ))m"
    printf "\r[%-${width}s] %3d/%d  ~%-4s left  %-70s" "$(printf "%${filled}s" | tr ' ' '#')" "$finished" "$total" "$left" "$1"
}

run_main() {  # run_main "<label>" <main.py arguments...>
    local label=$1
    shift
    progress "$label"
    if ! uv run main.py "$@" >> "$LOG" 2>&1; then
        echo; echo "Run failed: $label. Last lines of $LOG:"; tail -20 "$LOG"; exit 1
    fi
    finished=$(( finished + 1 ))
}
