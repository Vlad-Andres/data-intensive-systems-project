DATABASE ?= data/Database_small.txt
GRAPH ?=
OUTPUT ?= graphs$(GRAPH).html

.PHONY: install visualise clean

install:
	uv sync

visualise:
	uv run python src/visualize_graph.py $(DATABASE) $(GRAPH) --output $(OUTPUT)
	open $(OUTPUT)

clean:
	rm -f graphs*.html
