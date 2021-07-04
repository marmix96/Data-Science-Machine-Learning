import pickle
from pathlib import Path

import click
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from rich import console
from rich import progress

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
PLOTS_DIR = BASE_DIR / "plots"
PREPROCESSED_OBJECT = BASE_DIR / "preprocessed.o"
STOCKS_OBJECT = BASE_DIR / "raw.o"
HEADERS = ["date", "open", "high", "low", "close", "volume", "openint"]


def load_stocks() -> pd.DataFrame:
    if STOCKS_OBJECT.exists():
        with console.Console().status("Loading stocks..."):
            with open(STOCKS_OBJECT, "rb") as stream:
                return pickle.load(stream)
    stocks = []
    progress_bar = progress.Progress(
        "{task.description}",
        progress.BarColumn(),
        "{task.completed} of {task.total} ({task.percentage:>6.2f}%)",
        progress.TimeRemainingColumn(),
        progress.TimeElapsedColumn(),
    )
    with progress_bar:
        for stock in progress_bar.track(
            list(sorted(DATA_DIR.iterdir())), description="Loading stocks..."
        ):
            stock_name = stock.name.split(".", 1)[0]
            df = pd.read_csv(stock, header=0, names=HEADERS)
            # Empty CSV.
            if df.size == 0:
                continue
            df["stock"] = stock_name
            df = df[["date", "stock", "open", "low", "high", "close", "volume"]]
            stocks.append(df)
    with console.Console().status("Merging stocks..."):
        stocks = pd.concat(stocks, ignore_index=True)
        stocks["date"] = pd.to_datetime(stocks["date"])
        stocks["open"] = stocks["open"].astype(np.float64)
        stocks["high"] = stocks["high"].astype(np.float64)
        stocks["low"] = stocks["low"].astype(np.float64)
        stocks["close"] = stocks["close"].astype(np.float64)
        stocks["volume"] = (stocks["volume"] * 0.1).astype(np.uint32)
        stocks = stocks.set_index(["date", "stock"]).sort_index()
    with open(STOCKS_OBJECT, "wb") as stream:
        pickle.dump(stocks, stream)
    return stocks


def preprocess_stocks(stocks: pd.DataFrame) -> pd.DataFrame:
    if PREPROCESSED_OBJECT.exists():
        with console.Console().status("Loading preprocessed stocks..."):
            with open(PREPROCESSED_OBJECT, "rb") as stream:
                return pickle.load(stream)
    with console.Console().status("Preprocessing stocks..."):
        stocks["buy-open_sell-high"] = ((stocks["high"] * 0.99) / (stocks["open"] * 1.01)).replace(
            [-np.inf, np.inf], np.nan
        )
        stocks["buy-low_sell-close"] = ((stocks["close"] * 0.99) / (stocks["low"] * 1.01)).replace(
            [-np.inf, np.inf], np.nan
        )
        stocks["winratio"] = np.where(
            stocks["buy-open_sell-high"] > stocks["buy-low_sell-close"],
            stocks["buy-open_sell-high"],
            stocks["buy-low_sell-close"],
        )
        stocks = stocks[stocks["winratio"] >= 1.01].copy(deep=True)
        stocks["buy"] = np.where(
            stocks["buy-open_sell-high"] > stocks["buy-low_sell-close"],
            stocks["open"] * 1.01,
            stocks["low"] * 1.01,
        )
        stocks["sell"] = np.where(
            stocks["buy-open_sell-high"] > stocks["buy-low_sell-close"],
            stocks["high"] * 0.99,
            stocks["close"] * 0.99,
        )
        stocks["buy-action"] = np.where(
            stocks["buy-open_sell-high"] > stocks["buy-low_sell-close"],
            "buy-open",
            "buy-low",
        )
        stocks["sell-action"] = np.where(
            stocks["buy-open_sell-high"] > stocks["buy-low_sell-close"],
            "sell-high",
            "sell-close",
        )
        stocks = stocks[["buy", "sell", "volume", "buy-action", "sell-action"]]
    with open(PREPROCESSED_OBJECT, "wb") as stream:
        pickle.dump(stocks, stream)
    return stocks


def solve_small():
    stocks = load_stocks()
    last_date = stocks.index.get_level_values("date").values[-1]
    stocks = preprocess_stocks(stocks)
    output = RESULTS_DIR / "small.txt"
    plot = PLOTS_DIR / "small.png"
    stats = pd.DataFrame(
        np.nan,
        index=pd.date_range(
            start=pd.Timestamp(year=1960, month=1, day=1),
            end=last_date,
            freq="D",
            name="date",
        ),
        columns=["balance", "portfolio"],
    )
    stats["balance"][0] = 1.0
    balance = 1.0
    n = 0
    actions = []
    progress_bar = progress.Progress(
        "{task.description}",
        progress.BarColumn(),
        "{task.completed} of {task.total} ({task.percentage:>6.2f}%)",
        progress.TimeRemainingColumn(),
        progress.TimeElapsedColumn(),
    )
    timestamp: pd.Timestamp
    daystocks: pd.DataFrame
    with progress_bar:
        for timestamp, daystocks in progress_bar.track(
            list(stocks.groupby(by=["date"])), description="Solving small..."
        ):
            winnings = 0
            least_winnings = 1e7 if balance > 1e8 else balance * 2 ** -(1e-8 * balance)
            daystocks = daystocks.droplevel("date")
            daystocks["buyable"] = balance // daystocks["buy"]
            daystocks["volume"] = daystocks[["volume", "buyable"]].min(axis=1).astype(np.uint32)
            daystocks = daystocks[daystocks["volume"] > 0]
            daystocks["winnings"] = (
                daystocks["volume"] * (daystocks["sell"] - daystocks["buy"])
            ).astype(np.float64)
            daystocks = daystocks[daystocks["winnings"] >= least_winnings]
            if daystocks.size == 0:
                continue
            daystocks = daystocks.sort_values("winnings", ascending=False).head(1)
            for stock_name, stock in daystocks.iterrows():
                n += 2
                buy, sell, volume = stock["buy"], stock["sell"], stock["volume"]
                buy_action, sell_action = stock["buy-action"], stock["sell-action"]
                balance -= buy * volume
                winnings += sell * volume
                actions.append([timestamp, buy_action, stock_name, volume])
                actions.append([timestamp, sell_action, stock_name, volume])
            balance += winnings
            stats["balance"].loc[timestamp] = balance
            if n == 1000:
                break
    actions = pd.DataFrame(actions, columns=["date", "action", "stock", "volume"])
    actions["action"] = pd.Categorical(
        actions["action"],
        categories=["buy-open", "buy-low", "sell-high", "sell-close"],
        ordered=True,
    )
    actions = actions.sort_values(by=["date", "action"])
    actions["stock"] = actions["stock"].str.upper()
    stats = stats.fillna(method="pad")
    output.parent.mkdir(parents=True, exist_ok=True)
    plot.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as stream:
        stream.write(f"{actions.shape[0]}\n")
        actions.to_csv(stream, sep=" ", header=False, index=False, date_format="%Y-%m-%d")
    stats.plot.area(figsize=(20, 10))
    plt.title("Balance and portfolio through time after 1000 transactions")
    plt.xlabel("Date")
    plt.ylabel("Dollars")
    plt.savefig(plot, bbox_inches="tight")
    print(n, balance)
    return balance, actions, stats


def solve_large():
    stocks = load_stocks()
    last_date = stocks.index.get_level_values("date").values[-1]
    stocks = preprocess_stocks(stocks)
    output = RESULTS_DIR / "large.txt"
    plot = PLOTS_DIR / "large.png"
    stats = pd.DataFrame(
        np.nan,
        index=pd.date_range(
            start=pd.Timestamp(year=1960, month=1, day=1),
            end=last_date,
            freq="D",
            name="date",
        ),
        columns=["balance", "portfolio"],
    )
    stats["balance"][0] = 1.0
    balance = 1.0
    n = 0
    actions = []
    progress_bar = progress.Progress(
        "{task.description}",
        progress.BarColumn(),
        "{task.completed} of {task.total} ({task.percentage:>6.2f}%)",
        progress.TimeRemainingColumn(),
        progress.TimeElapsedColumn(),
    )
    timestamp: pd.Timestamp
    daystocks: pd.DataFrame
    with progress_bar:
        for timestamp, daystocks in progress_bar.track(
            list(stocks.groupby(by=["date"])), description="Solving large..."
        ):
            winnings = 0
            daystocks = daystocks.droplevel("date")
            daystocks["buyable"] = balance // daystocks["buy"]
            daystocks["volume"] = daystocks[["volume", "buyable"]].min(axis=1).astype(np.uint32)
            daystocks = daystocks[daystocks["volume"] > 0]
            if daystocks.size == 0:
                continue
            daystocks["winnings"] = (
                daystocks["volume"] * (daystocks["sell"] - daystocks["buy"])
            ).astype(np.float64)
            daystocks = daystocks.sort_values(["winnings"], ascending=False).head(80)
            for stock_name, stock in daystocks.iterrows():
                buy, sell, volume = stock["buy"], stock["sell"], stock["volume"]
                buy_action, sell_action = stock["buy-action"], stock["sell-action"]
                if balance < buy:
                    continue
                n += 2
                buyable = int(min(volume, balance // buy))
                balance -= buy * buyable
                winnings += sell * buyable
                actions.append([timestamp, buy_action, stock_name, buyable])
                actions.append([timestamp, sell_action, stock_name, buyable])
                if n == 1000000:
                    break
            balance += winnings
            stats["balance"].loc[timestamp] = balance
            if n == 1000000:
                break
    actions = pd.DataFrame(actions, columns=["date", "action", "stock", "volume"])
    actions["action"] = pd.Categorical(
        actions["action"],
        categories=["buy-open", "buy-low", "sell-high", "sell-close"],
        ordered=True,
    )
    actions = actions.sort_values(by=["date", "action"])
    actions["stock"] = actions["stock"].str.upper()
    stats = stats.fillna(method="pad")
    output.parent.mkdir(parents=True, exist_ok=True)
    plot.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as stream:
        stream.write(f"{actions.shape[0]}\n")
        actions.to_csv(stream, sep=" ", header=False, index=False, date_format="%Y-%m-%d")
    stats.plot.area(figsize=(20, 10))
    plt.title("Balance and portfolio through time after 1000000 transactions")
    plt.xlabel("Date")
    plt.ylabel("Dollars")
    plt.savefig(plot, bbox_inches="tight")
    print(n, balance)
    return balance, actions, stats


@click.group(name="solve", help="Solve the stocks problem.")
def main():
    pass


@main.command(name="small", help="Solve the stocks problem with at most 1000 transactions.")
def main_small():
    solve_small()


@main.command(name="large", help="Solve the stocks problem with at most 1000000 transactions.")
def main_large():
    solve_large()


if __name__ == "__main__":
    main()
