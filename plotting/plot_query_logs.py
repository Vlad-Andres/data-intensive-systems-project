"""
One bar chart per query log type: how many times each distinct query is asked, the most asked in the middle.
The 4 types have the same shape for every database, so one database's logs are drawn (default: DatabaseX_7).

    uv run python -m plotting.plot_query_logs [--database 7]

Saves plots/q_logs/QLog_<type>_<name>.png.
"""
import argparse
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Only write image files, never open a window.

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
LOG_TYPES = {"1": "popularity", "2": "shifting interest", "3": "complex variables", "4": "sub-queries"}
BAR_COLOR, INK, MUTED_INK, GRID = "#2a78d6", "#1f1f1e", "#5f5e5a", "#e4e3df"


def plot_query_log(query_log_file: Path, log_type: str, output_path: Path) -> None:
    lines = [line.strip() for line in query_log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = sorted(Counter(lines).values(), reverse=True)
    bell = counts[1::2][::-1] + counts[0::2]  # Most asked in the middle, the others alternating to both sides.
    queries_for_half = next(index for index in range(1, len(counts) + 1) if sum(counts[:index]) >= len(lines) / 2)

    title = f"QLog_{log_type} · {LOG_TYPES[log_type]} (example: {query_log_file.stem})"

    figure, axes = plt.subplots(figsize=(7, 3.6), layout="constrained")
    axes.bar(range(len(bell)), bell, color=BAR_COLOR, width=0.8)
    axes.set_title(
        f"{title}: {len(lines)} lines, {len(counts)} distinct queries\n"
        f"most asked: {counts[0]}× ({counts[0] / len(lines):.0%} of lines) · half of all lines come from {queries_for_half} of {len(counts)} queries",
        loc="left", fontsize=10, color=INK,
    )
    axes.set_xticks([])
    axes.set_xlabel("distinct queries (most asked in the middle)", fontsize=8, color=MUTED_INK)
    axes.set_ylabel("times asked", fontsize=8, color=MUTED_INK)
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))
    axes.yaxis.grid(True, color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(length=0, labelsize=8, labelcolor=MUTED_INK)
    for spine in axes.spines.values():
        spine.set_visible(False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, facecolor="#ffffff")
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="One bar chart per query log type.")
    parser.add_argument("--database", type=int, default=7, help="Whose query logs to draw (the shapes are the same for every database).")
    args = parser.parse_args()

    output_folder = PROJECT_DIRECTORY / "plots" / "q_logs"
    for log_type, name in LOG_TYPES.items():
        query_log_file = PROJECT_DIRECTORY / "data" / f"QLog{args.database}_{log_type}.txt"
        plot_query_log(query_log_file, log_type, output_folder / f"QLog_{log_type}_{name.replace(' ', '_')}.png")
    print(f"Saved {len(LOG_TYPES)} query log charts in {output_folder.relative_to(PROJECT_DIRECTORY)}")
