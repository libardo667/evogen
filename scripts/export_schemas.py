from __future__ import annotations

import argparse
from pathlib import Path

from evogen.schema import export_schemas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path, default=Path("schemas"))
    args = parser.parse_args()
    for path in export_schemas(args.directory):
        print(path)


if __name__ == "__main__":
    main()
