import os
from pathlib import Path
from backend.scripts import init_seed_data as seed
seed.SNAPSHOT_PATH=Path(os.environ["REVIEW_SNAPSHOT"])
seed.main()
