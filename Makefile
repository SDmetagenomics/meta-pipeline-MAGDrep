.PHONY: install install-checkm1 test test-all clean

# One-command install: creates the main conda env with all tools + the
# pipeline itself, plus the sibling env for the optional CheckM1 step.
install: install-checkm1
	mamba env create -f environment.yml --yes || \
		mamba env update -n magdrep -f environment.yml
	@echo ""
	@echo "Done. Activate with:  conda activate magdrep"
	@echo "CheckM1 lives in the sibling env 'magdrep-checkm1' — MAGDrep"
	@echo "will invoke it automatically when 'checkm1' is in --steps."

# Create the side env hosting CheckM1 (incompatible Python with CheckM2).
install-checkm1:
	mamba env create -f envs/checkm1.yml --yes || \
		mamba env update -n magdrep-checkm1 -f envs/checkm1.yml

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
