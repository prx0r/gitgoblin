.PHONY: install test certify serve demo clean
install:
	python -m pip install -e '.[dev]'
test:
	pytest -q
certify:
	python -m gitgoblin.certify --output build/CERTIFICATE.json
serve:
	gitgoblin serve --host 0.0.0.0 --port 8787
clean:
	rm -rf .pytest_cache .coverage htmlcov build/CERTIFICATE.json build/test.log
