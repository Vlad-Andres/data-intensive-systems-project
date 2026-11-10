Baseline dataset of group 15 (received by group 24), filtered so it follows the path syntax of the project description.
The original files are in ../Dataset24/.

FILES
Database15.txt  Unchanged copy of the graph database (3,370 graphs, 166,387 triples).
QLog15_1.txt    The query log without the queries that use two edge labels in a row.
                Named QLog<database>_<number>.txt, the name main.py expects.

WHAT WAS REMOVED
Queries with an edge label directly after another edge label, e.g. 3.holds.chequeCNY or
1001103.achUSD.achEUR.1002340.role."sink". The project description writes an unknown intermediate node as a
variable (5.married.X.city.Y), so these paths do not follow it; group 15's README documents them as an extension.

                    original   kept    removed
query lines         5,962      2,434   3,528 (59%)
distinct queries    1,726      1,160     566 (33%)

All kept queries parse with our parser, and none has a word in a node position. Most asked query in the kept log:
40 times; 962 distinct queries are asked once. 57% of the second-half lines were already asked in the first half.

RUN
uv run main.py --graph peer-dataset-test/Dataset24_fixed/Database15.txt --qlog peer-dataset-test/Dataset24_fixed/QLog15_1.txt \
    --graph_selection rounds --query_coverage distributed --importance_threshold 0.02 --tests True
