"""
Redraw every plot from the CSV files saved next to it, without running a reduction or Spark again. Use it after changing how
a plot looks:

    uv run python -m plotting.replot                     # everything in plots/
    uv run python -m plotting.replot --only comparison   # or: runs, comparison, small_databases, similarity_budget, baseline, measures, q_logs
"""
import argparse
from pathlib import Path

from plotting.plot_baseline import BASELINE_FOLDER, draw_all as draw_baseline
from plotting.plot_extra_comparisons import BUDGET_FOLDER, SMALL_FOLDER, draw_similarity_budgets, draw_small_databases
from plotting.plot_measures import draw_measures
from plotting.plot_method_comparison import COMPARISON_FOLDER, draw_all as draw_comparison
from plotting.plot_query_logs import draw_query_log
from plotting.plot_reduction import draw_run_plots

PLOTS_FOLDER = Path(__file__).resolve().parent.parent / "plots"


def replot_runs() -> None:
    folders = sorted(path.parent for path in (PLOTS_FOLDER / "runs").glob("*/run_info.json"))
    for number, folder in enumerate(folders, start=1):
        draw_run_plots(folder)
        print(f"\r  runs: {number}/{len(folders)}", end="", flush=True)
    print(f"\rRedrew the plots of {len(folders)} runs in plots/runs/")


def replot_comparison() -> None:
    if (COMPARISON_FOLDER / "results.csv").exists():
        draw_comparison()
    else:
        print("No plots/comparison/results.csv yet: run plotting/compare-methods.sh first.")


def replot_small_databases() -> None:
    if (SMALL_FOLDER / "results.csv").exists():
        draw_small_databases()
    else:
        print("No plots/comparison/small_databases/results.csv yet: run plotting/compare-small-databases.sh first.")


def replot_similarity_budget() -> None:
    if (BUDGET_FOLDER / "results.csv").exists():
        draw_similarity_budgets()
    else:
        print("No plots/comparison/similarity_budget/results.csv yet: run plotting/compare-similarity-budgets.sh first.")


def replot_baseline() -> None:
    if (BASELINE_FOLDER / "results.csv").exists():
        draw_baseline()
    else:
        print("No plots/baseline/results.csv yet: run plotting/baseline-comparison.sh first.")


def replot_measures() -> None:
    bases = sorted(path.with_suffix("") for path in (PLOTS_FOLDER / "measures").glob("*.csv"))
    for base in bases:
        draw_measures(base)
    print(f"Redrew {len(bases)} measure plots in plots/measures/")


def replot_query_logs() -> None:
    bases = sorted(path.with_suffix("") for path in (PLOTS_FOLDER / "q_logs").glob("*.csv"))
    for base in bases:
        draw_query_log(base)
    print(f"Redrew {len(bases)} query log plots in plots/q_logs/")


REPLOTS = {"runs": replot_runs, "comparison": replot_comparison, "small_databases": replot_small_databases,
           "similarity_budget": replot_similarity_budget, "baseline": replot_baseline, "measures": replot_measures, "q_logs": replot_query_logs}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redraw every plot from its CSV files.")
    parser.add_argument("--only", choices=list(REPLOTS), nargs="+", help="Only redraw these groups of plots.")
    args = parser.parse_args()
    for name in args.only or REPLOTS:
        REPLOTS[name]()
