"""The command: era5land-points <config file>. Exit code 0 if every location worked, 1 if any
failed, 2 if the config or the CDS key has a problem."""

import argparse
import sys

from era5land_points import config, pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="era5land-points",
        description="Download ERA5-Land's hourly series at the config's locations, summarise "
        "them into days, months and years, and write CSV files and a viewer page.",
    )
    parser.add_argument("config", help="the config file, such as config.yaml")
    args = parser.parse_args(argv)
    try:
        failed = pipeline.run(config.load(args.config))
    except config.ConfigError as error:
        print(f"The config has a problem: {error}", file=sys.stderr)
        return 2
    except pipeline.SetupError as error:
        print(f"Can't reach the Climate Data Store: {error}", file=sys.stderr)
        return 2
    return 1 if failed else 0
