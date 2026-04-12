.PHONY: install test test-all clean

# One-command install: creates conda env with all tools + the pipeline itself
install:
	mamba env create -f environment.yml --yes
	@echo ""
	@echo "Done. Activate with:  conda activate magdrep"

# Run unit tests (no external tools or databases needed)
test:
	python -m pytest tests/ -v --ignore=tests/test_integration.py

# Run all tests including slow integration tests (requires tools + databases)
test-all:
	python -m pytest tests/ -v

# Download the 50 test genomes from GitHub Release
test-genomes:
	python tests/data/download_test_genomes.py --source github

# Remove build artifacts
clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
