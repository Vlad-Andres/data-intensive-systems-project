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