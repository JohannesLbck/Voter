# Constraint Identification

This folder documents the temporal constraint identification case study from the blood guide. Full text blood guide in pdf can not be provided for copyright protection but can be found
on the official website of the [EDQM](https://www.edqm.eu/en/blood-guide). The full list of terms used for identification can be checked in the pdfsearcher.py script.

## Files

- **pdfsearcher.py** — Extracts numbered rules from PDF files and filters those containing time-related keywords (e.g., "hours", "no later than", "period").
- **ConstraintIdentificationTables.csv** — Contains the final set of rule types and documentation of the attribute/focus coding steps
- **output.csv** — Generated output of matched temporal rules.

## Usage

```bash
python pdfsearcher.py <file1.pdf> [file2.pdf ...]
```

The script:
1. Extracts all numbered rules from each PDF.
2. Matches rules containing temporal keywords (time units, deadlines, periods).
3. Writes matched rules to `output.csv` and prints them to the console.
