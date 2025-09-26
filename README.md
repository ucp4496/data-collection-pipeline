# Data Collection Pipeline

This repository contains the **Data Collection Pipeline** project for **Model-Driven Development**.

---

## Running the CLI

To fetch commits and export them to a CSV file, run:

```bash
python -m src.repo_miner fetch-commits --repo owner/repo [--max 100] --out commits.csv
```

- Replace `owner/repo` with the GitHub repository you want to analyze.  
- The `--max` flag is optional and limits the number of commits fetched.  
- The `--out` flag specifies the output file (e.g., `commits.csv`).  

**Note:** Depending on your configuration, you may need to use `python3` instead of `python`.

---

## Dependencies

If you encounter missing dependency warnings, install the required packages:

```bash
pip install -r requirements.txt
```

Or, on some systems:

```bash
pip3 install -r requirements.txt
```

---

## Running Tests

Run all tests using:

```bash
pytest
```

For more detailed output, use the verbose flag:

```bash
pytest -v
```
