# -*- coding: utf-8 -*-
"""
Created on Thu Nov  5 11:45:17 2026

@author: deni_
"""


from pathlib import Path
import os
import sys

# Project directory
project_dir = Path(r"C:\Users\deni_\OneDrive - USNH\Desktop\post doc\SSECR - course _ project\era5land-points_ssecr")

config_file = project_dir / "my-config.yaml"

# Make the project directory the working directory.
# This allows the YAML to find sites.csv using its relative path.
os.chdir(project_dir)

print("Python environment:", sys.executable, flush=True)
print("Project directory:", Path.cwd(), flush=True)
print("Config file:", config_file, flush=True)

# Confirm that the config exists
if not config_file.exists():
    raise FileNotFoundError(f"Config file not found: {config_file}")

# Import and run the package's actual command-line entry point
from era5land_points.cli import main

print("\nStarting ERA5-Land extraction...\n", flush=True)

exit_code = main([str(config_file)])

print("\n" + "=" * 60)
if exit_code == 0:
    print("Extraction completed successfully.")
elif exit_code == 1:
    print("Extraction finished, but one or more locations failed.")
else:
    print("Extraction stopped because of a configuration or setup problem.")
print("Exit code:", exit_code)
print("=" * 60)
