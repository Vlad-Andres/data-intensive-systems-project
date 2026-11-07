## DIS project on graph database reduction


![graphs visualised](images/graphs-small.png)

Big IMDb database: [images/imdb_big](images/imdb_big/README.md)

### Dataset versions (`make datasets`)
| File | Graphs | Max edges | Semantic |
|---|---|---|---|
| `data/DatabaseX_1.txt` | 20 | 10 | low |
| `data/DatabaseX_2.txt` | 20 | 10 | high |
| `data/DatabaseX_3.txt` | 20 | 50 | low |
| `data/DatabaseX_4.txt` | 20 | 50 | high |
| `data/DatabaseX_5.txt` | 1000 | 10 | low |
| `data/DatabaseX_6.txt` | 1000 | 10 | high |
| `data/DatabaseX_7.txt` | 1000 | 50 | low |
| `data/DatabaseX_8.txt` | 1000 | 50 | high (= `imdb_big.txt`) |

IMDb lists ~10 main people per movie, so low-semantic graphs never have more than 16 edges.

Images of each version: [images/datasets](images/datasets/README.md)

### Makefile command shortcuts
```bash
make visualise              # makes graphs.html
make visualise GRAPH=2      # only graph 2 in graph2.html
make visualise DATABASE=data/imdb_big.txt GRAPH="0 1" HEIGHT=1600px   # graphs 0 and 1 in graphs0-1.html
make imdb-images            # images of the big IMDb database
make datasets               # the 8 dataset versions (+ filtered QLogs if data/QLogX.txt exists)
make dataset-images         # images of the 8 dataset versions

make install                # installs the project with uv
make clean                  # removes the generated html graphs
```

### Reduce Function Metric

To test the query coverage of a DB (after a Reduce), run:
```
python3 src/QLog_satisfaction.py <DB_path> <QLog_path>
```

### Run the reduction

Options:

--graph_file: input graph database.
--query_log_file: input query log; its filename should look like
QLog<db>_<number>.txt.
--importance_threshold: fraction of graphs to keep (default: 0.9).
--tests True: test the reduced database against other qlogs.
--performance True: print timing information.
--graph_similarity


Example:
```
python3 main.py --graph data/DatabaseX_1.txt --qlog  data/QLog1_1.txt --graph_similarity True --similarity_budget 0.2 --query_coverage distributed --graph_selection rounds --check_qlog_satisfaction False --tests True --performance True
```

### Examples

Step-by-step scripts in `examples/`, from the simplest reduction to the full one (run from anywhere, they use `uv` and Java 21):
```bash
./examples/01_naive_full_coverage.sh           # sort once by fully answered queries
./examples/02_naive_partial_coverage.sh        # + partly answered queries count
./examples/03_naive_distributed_coverage.sh    # + a query's point is split over its answering graphs
./examples/04_greedy_rounds.sh                 # greedy: one graph per round, gains recomputed
./examples/05_greedy_with_graph_similarity.sh  # + graph similarity
./examples/06_graph_similarity_budget_tradeoff.sh
./examples/07_large_keep_with_timings.sh
./examples/08_compare_methods.sh               # all methods on databases 5-8 × 4 query logs (~48 runs), one chart per database
./examples/09_query_log_charts.sh               # one bar chart per query log type: how often each query is asked
./examples/10_compare_measures.sh             # score of every graph under full, partial and distributed, side by side
```
Each run prints the test coverage and saves two plots in `plots/<run settings>/`: `answered_queries.png` (which queries are still answered) `kept_graphs.png` (which graphs of the database were kept) and `future/preserved_answers.png` (share of answers kept for the unseen queries, if a user needs 1, 3, 10 or all answers). They use `data/DatabaseX_7.txt` with `data/QLog7_2.txt`, keeping 2% of the graphs; change this with `GRAPH`, `QLOG` and `KEEP`, e.g. `QLOG=data/QLog7_4.txt ./examples/04_greedy_rounds.sh`.
