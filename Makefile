.PHONY: run test demo

run:
	py run.py --config examples/config_test.csv

test:
	py -m unittest discover -s tests -v

demo:
	py tests/scenarios.py
