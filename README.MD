## DIS project on graph database reduction


![graphs visualised](images/graphs-small.png)

Big IMDb database: [images/imdb_big](images/imdb_big/README.md)

### Makefile command shortcuts
```bash
make visualise              # makes graphs.html
make visualise GRAPH=2      # only graph 2 in graph2.html
make visualise DATABASE=data/imdb_big.txt GRAPH="0 1" HEIGHT=1600px   # graphs 0 and 1 in graphs0-1.html
make imdb-images            # images of the big IMDb database

make install                # installs the project with uv
make clean                  # removes the generated html graphs
```