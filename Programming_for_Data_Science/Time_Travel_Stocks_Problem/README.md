# Stocks Problem

Welcome to the `stocks problem` solution guide.

## Setup

### Download `kaggle` dataset.

Follow [this link](https://www.kaggle.com/borismarjanovic/price-volume-data-for-all-us-stocks-etfs/version/3)
and download the zip file. Unzip the data and move all `Stocks` data to a new directory called
`data`.

```bash
unzip archive.zip # Replace archive.zip with the correct filename of the downloaded file.
mv Stocks data
rm -rf Data ETFs
```

### Install requirements

The project was run with `python3.8` and should be able to run with all python
versions above this. Install all the required dependencies:

```bash
pip install -r requirements.txt
```

## Solve

To solve the 1000 transactions run:

```bash
python solve.py small
```

To solve the 1000000 transactions run:

```bash
python solve.py large
```

**Note:** both scripts assume that the data lies in a directory `data` within the same directory as
the `solve.py` script. If you have the data saved somewhere else you can manipulate the filepath by
modifying the variable `DATA_DIR`. Also, there are two files produced for caching the preprocessed
data called `raw.o` and `preprocessed.o` in the same directory as `solve.py`.

**Note:** the resulting txts are written to a new directory `results` created in the same directory
as `solve.py`, while the plots are similarly written to a directory `plots`. `small` and `large`
are used as basenames for the resulting files, `small` for 1000 transactions, while `large` for
1000000 transactions.

**Note:** both scripts should take at most 5 minutes (each) to run.
