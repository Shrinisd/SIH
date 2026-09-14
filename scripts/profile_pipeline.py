import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.benchmark_end_to_end import run_benchmarks

if __name__ == "__main__":
    success = run_benchmarks()
    sys.exit(0 if success else 1)
