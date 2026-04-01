"""Read ordinary or losslessly compressed experiment JSON."""

import gzip
import json
from pathlib import Path


def read_results(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)
