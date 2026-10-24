DATABASE ?= data/Database_small.txt
GRAPH ?=
HEIGHT ?= 750px
space := $(subst ,, )
OUTPUT ?= graphs$(subst $(space),-,$(strip $(GRAPH))).html
IMDB_RAW = data/imdb_raw
IMDB_FILES = title.basics title.ratings title.principals title.crew name.basics
CHROME ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
SCREENSHOT = "$(CHROME)" --headless=new --hide-scrollbars --virtual-time-budget=900000
# $(call image,database,graphs (empty = all),name,extra visualise options) -> html/name.html + images/name.png
image = mkdir -p $(dir html/$(3)) $(dir images/$(3)) && \
	uv run python src/visualize_graph.py $(1) $(2) --height 95vh $(4) --output html/$(3).html && \
	$(SCREENSHOT) --window-size=1600,1620 "--screenshot=$$PWD/images/$(3).png" "file://$$PWD/html/$(3).html"
SEED ?= 1
QLOG ?= data/QLogX.txt
# $(call version,number,graphs,max edges,semantic); filters QLOG too when it exists
version = uv run python src/derive.py data/imdb_big.txt --seed $(SEED) --graphs $(2) --max-edges $(3) \
	--semantic $(4) --output data/DatabaseX_$(1).txt \
	$(if $(wildcard $(QLOG)),--qlog $(QLOG) --qlog-output data/QLog_$(1).txt)

.PHONY: install visualise clean imdb-raw imdb imdb-images datasets dataset-images

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
	$(call image,data/imdb_big.txt,0 1,imdb_big/two-movies)
	$(call image,data/imdb_big.txt,,imdb_big/all,--overview)

# 20-graph versions: all graphs; 1000-graph versions: the first 2 movies
dataset-images:
	$(call image,data/DatabaseX_1.txt,,datasets/DatabaseX_1)
	$(call image,data/DatabaseX_2.txt,,datasets/DatabaseX_2)
	$(call image,data/DatabaseX_3.txt,,datasets/DatabaseX_3)
	$(call image,data/DatabaseX_4.txt,,datasets/DatabaseX_4)
	$(call image,data/DatabaseX_5.txt,0 1,datasets/DatabaseX_5)
	$(call image,data/DatabaseX_6.txt,0 1,datasets/DatabaseX_6)
	$(call image,data/DatabaseX_7.txt,0 1,datasets/DatabaseX_7)
	$(call image,data/DatabaseX_8.txt,0 1,datasets/DatabaseX_8)

datasets:
	$(call version,1,20,10,low)
	$(call version,2,20,10,high)
	$(call version,3,20,50,low)
	$(call version,4,20,50,high)
	$(call version,5,1000,10,low)
	$(call version,6,1000,10,high)
	$(call version,7,1000,50,low)
	$(call version,8,1000,50,high)
