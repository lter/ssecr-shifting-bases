# Shifting Baselines [SSECR 2026] 

Principal Investigators: Emerson Conrad-Rooney, Nyika Campbell, Deni Murray, Asher Marvy, Kalea Nippert-Churchman

## Research Questions
* Q1: Are temperatures in control conditions in long-term ecology studies changing over time? 
* Q2: How many existing studies are measuring or manipulating temperature in their treatment conditions, and is the difference between treatment and control temperature for these studies changing over time due to shifting baselines.
* Q3: Are experimental results in existing long-term ecology studies being impacted by shifting baselines? (cover in discussion section)

## Repo to-do list
- [ ] Decide on more GitHub Organization Structure. See "File Structure" section below for sugestions
- [x] Discuss use of Agents in Repo, set up Agents.md and Prompt Action Log if using. Ok for coding, not to touch or view non-public data. Human-review all outputs.

## Repository layout
Briefly describe the purpose of major scripts as you create them!

### File Structure
*Map of each folder in the first three levels and major files in the first three levels. placeholders for repetitive naming ok*

*This is a potential structure that has worked for Nyika in the past, but we don't have to use this. This would be useful if data management (cleaning and manupulation) are seperate from data analysis. A different structure would proably serve better for a more integrated workflow.*

```
seecr-shifting-baselines/
├── data-management/            # raw data intake, cleaning, reshaping, standardization, creation of derived data
├── data-analysis/              # Finished analysis scripts w/ documentaion
├── sandbox/                      # A place for working, experimental or in-process scripts
│   ├── data/                     # Git-ignored folder for locally stored data accessible from anyone's working folder
│   └── name-working/             # Folder for each person's personal experimental work
├── x_scratch/                    # git-ignored scratch space for locally stored material
└── README.md
```

### Item Descriptions

*descriptions of each folder in the first three levels and major files in the first three levels. placeholders for repetitive naming ok*

| Item | Description |
| --- | --- |
| `data-management/` | raw data intake, cleaning, and derived data; numbered workflow scripts |
| `data-analysis/` | finalized, debugged, and documented scripts that contribute to our final product |
| `sandbox/` | exploratory plots and summary stats; one subfolder per person or collaborative workflow |
| `x_scratch/` | git-ignored scratch space for local files |

### Script & Folder Explanations

Briefly describe the purpose of major scripts as you create them!

| Script | Purpose | Location |
| --- | --- | --- |
| `import-drive-data.R` | Reads the data log from Google Drive and downloads each dataset flagged `read_into_git == TRUE` into a local, git-ignored folder | `1_data-management/tools/` |
| `mesi_wide_long_conversion.R` | Converts the MESI main table from wide to long format (one row per control/treatment comparison). Adapted from the [public MESI data package](https://doi.org/10.5281/zenodo.10423853) | `1_data-management/tools/` |
| `01_wrangle-datasets.R` | Cleans and reshapes each raw dataset (Song, Corre, MESI) individually so they're ready to harmonize; writes derived data to `data/derived_data/` | `1_data-management/scripts/` |
| `02_harmonize-datasets.R` | Uses `ltertools::harmonize()` and a column key to rename columns across the derived datasets into a shared, combined format | `1_data-management/scripts/` |
| `SongDataCompile.py` | Compiles the raw Song et al. 2019 CSVs, cleans/renames columns, standardizes sampling years, and calculates study duration per experiment | `sandbox/deni-working/` |

## Supplementary Resources

LTER Scientific Computing Team [website](https://lter.github.io/scicomp/) & NCEAS [Resources for Working Groups](https://www.nceas.ucsb.edu/working-group-resources)

## Style Guidelines

### Naming Conventions

**General:** Generally naming relies on slugs in `kebab-case` to carry nominal information about file contents or category and prefixes or suffixes attached with `snake_case` to indicate ordinal metadata such as order, timing, provenance or versioning

**Scripts:** Script naming conventions:

**Script Organization:** 
Potential Script organization

- `# PURPOSE AND USE:`
- `# PART 1: SETUP ----` (libraries and sourcing using `here`)
- `# PART 2: USER INPUTS ----` (keep user inputs and switches in one place)
- `# PART 3: READ IN FILES ----`
- `# PART 4: DEFINE FUNCTIONS ----` (if not sourced from another script)
- `# PART 5: (other things the script does) ----`
- `# PART X: SAVE OUTPUTS ----` (and report out that script is done. This always last.)

**Outputs:** outputs from scripts should be gitignored and stored in an `output` folder. A numeric or alphanumeric prefix may indicate which script the output came from, and / or what type of data it is. Output names should be descriptive, even if long, since outputs are often shared without context. 

**README:** All READMEs in all subdirectories should be named `README`. The first line of each should specify the location of the readme in the following format: `# README: repo-name/directory/subdirectory`. Expressive naming should ensure the file path indicates what the readme is about.
* README files should get increasingly more specific and should refer only to contents at lower organization levels.
* README may contain to-do lists or repo status updates
