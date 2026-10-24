DATABASE ?= data/Database_small.txt
GRAPH ?=
HEIGHT ?= 750px
space := $(subst ,, )
OUTPUT ?= graphs$(subst $(space),-,$(strip $(GRAPH))).html
IMDB_RAW = data/imdb_raw
IMDB_FILES = title.basics title.ratings title.principals title.crew name.basics
IMDB_IMAGES = images/imdb_big
CHROME ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
SCREENSHOT = "$(CHROME)" --headless=new --hide-scrollbars --virtual-time-budget=900000

.PHONY: install visualise clean imdb-raw imdb imdb-images

install:
	uv sync

visualise:
	uv run python src/visualize_graph.py $(DATABASE) $(GRAPH) --height $(HEIGHT) --output $(OUTPUT)
	open $(OUTPUT)

clean:
	rm -f graphs*.html

imdb-raw:
	mkdir -p $(IMDB_RAW)
	for f in $(IMDB_FILES); do curl -sSfo $(IMDB_RAW)/$$f.tsv.gz https://datasets.imdbws.com/$$f.tsv.gz; done

imdb:
	uv run python data_movie_imbd/converter.py --source $(IMDB_RAW) --output data/imdb_big.txt \
		--max-movies 1000 --max-graphs 1000 --max-edges-for-each-movie 50

imdb-images:
	uv run python src/visualize_graph.py data/imdb_big.txt 0 1 --height 1600px --output $(IMDB_IMAGES)/two-movies.html
	$(SCREENSHOT) --window-size=1600,1620 "--screenshot=$$PWD/$(IMDB_IMAGES)/two-movies.png" "file://$$PWD/$(IMDB_IMAGES)/two-movies.html"
	uv run python src/visualize_graph.py data/imdb_big.txt --height 1600px --overview --output $(IMDB_IMAGES)/all.html
	$(SCREENSHOT) --window-size=1600,1620 "--screenshot=$$PWD/$(IMDB_IMAGES)/all.png" "file://$$PWD/$(IMDB_IMAGES)/all.html"
	rm $(IMDB_IMAGES)/*.html
