.PHONY: run test demo graph

run:
	py run.py --config examples/config_test.csv

test:
	py -m unittest discover -s tests -v

demo:
	py tests/scenarios.py

graph:
	py run.py --config examples/config_graph_cycle.csv --graph
