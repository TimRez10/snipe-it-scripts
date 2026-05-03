import sys
from pathlib import Path

# Add project root to sys.path for tests (so 'modules' can be imported)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))