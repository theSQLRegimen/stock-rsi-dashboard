 
## Refactored Script

# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
import numpy as np
import time

from sqlalchemy import create_engine, text


# ---------------------------------
# CONFIG
# ---------------------------------

engine = create_engine(
    "mssql+pyodbc://@localhost\\SQLEXPRESS/optionsregimen"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)

START_DATE = "2023-01-01"
DOWNLOAD_BATCH_SIZE = 100
LOAD_CHUNK_SIZE = 50000
PAUSE_SECONDS = 2


# ---------------------------------
# EXTRACT TICKERS
# ---------------------------------

def get_tickers(engine):

    query = """
        SELECT ticker
        FROM dbo.stocks_master
        WHERE ticker IS NOT NULL
    """

    df = pd.read_sql(query, engine)

    return df.ticker.tolist()


# ---------------------------------
# STOCK LOOKUP
# ---------------------------------

def get_stock_lookup(engine):

    query = """
        SELECT stockid,
               ticker
        FROM dbo.stocks_master
    """

    df = pd.read_sql(query, engine)

    return dict(
        zip(
            df.ticker,
            df.stockid
        )
    )

# ---------------------------------
# TECHNICALS
# ---------------------------------

def compute_rsi_tv(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/period,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/period,
        min_periods=period
    ).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100/(1+rs))

    return rsi


# ---------------------------------
# BATCH DOWNLOAD
# ---------------------------------

def download_batch(tickers, start_date):

    try:

        print(
            f"Downloading {len(tickers)} tickers"
        )

        df = yf.download(
            tickers,
            start=start_date,
            group_by='ticker',
            auto_adjust=False,
            progress=False,
            threads=True
        )

        if df.empty:
            return pd.DataFrame()

        frames = []

        for ticker in tickers:

            try:
                tdf = df[ticker].copy()
            except:
                continue

            if tdf.empty:
                continue

            tdf = (
                tdf
                .reset_index()
                .rename(
                    columns={
                        "Date":"price_date",
                        "Close":"price_close",
                        "High":"price_high",
                        "Low":"price_low"
                    }
                )
            )

            tdf["ticker"] = ticker

            frames.append(
                tdf[
                    [
                        "ticker",
                        "price_date",
                        "price_close",
                        "price_high",
                        "price_low"
                    ]
                ]
            )

        if not frames:
            return pd.DataFrame()

        return pd.concat(
            frames,
            ignore_index=True
        )

    except Exception as e:

        print(
            f"Batch failed: {e}"
        )

        return pd.DataFrame()


# ---------------------------------
# TRANSFORM
# ---------------------------------

def transform_stock_data(df, stock_lookup):

    if df.empty:
        return df

    print(
        "Transform starting..."
    )

    df = df.copy()

    df["stockid"] = (
        df["ticker"]
        .map(stock_lookup)
    )

    df = df.dropna(
        subset=["stockid"]
    )

    df["price_date"] = pd.to_datetime(
        df["price_date"]
    )

    df = df.sort_values(
        [
            "stockid",
            "price_date"
        ]
    )


    # RSI
    df["rsi"] = (
        df.groupby(
            "stockid"
        )["price_close"]
        .transform(
            lambda x:
            compute_rsi_tv(x)
        )
    )


    # 52 week high
    df["week_52_high"] = (
        df.groupby(
            "stockid"
        )["price_high"]
        .transform(
            lambda x:
            x.rolling(
                252,
                min_periods=1
            ).max()
        )
    )


    df = df[
        [
            "stockid",
            "price_date",
            "price_close",
            "price_high",
            "price_low",
            "rsi",
            "week_52_high"
        ]
    ]

    df = df.replace(
        {np.nan:None}
    )

    return df

# ---------------------------------
# Truncate
# ---------------------------------

def truncate_stock_data(engine):
    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE stock_data;"))
            conn.commit()
        print("Table stock_data truncated successfully.")
    except Exception as e:
        print(f"Error truncating table: {e}")

# ---------------------------------
# LOAD
# ---------------------------------

def load_dataframe_to_sql(
    df,
    table_name,
    engine,
    chunk_size=50000
):

    if df.empty:
        return

    query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = :table_name
    """

    with engine.connect() as conn:

        cols = [
            r[0]
            for r in conn.execute(
                text(query),
                {
                    "table_name":table_name
                }
            )
        ]


    df_cols = [
        c for c in df.columns
        if c in cols
    ]


    insert_sql = text(
        f"""
        INSERT INTO dbo.{table_name}
        ({','.join(df_cols)})
        VALUES
        ({','.join(f':{c}' for c in df_cols)})
        """
    )


    total=0

    for start in range(
        0,
        len(df),
        chunk_size
    ):

        chunk = df.iloc[
            start:start+chunk_size
        ]

        rows = chunk[
            df_cols
        ].to_dict(
            orient='records'
        )

        with engine.begin() as conn:
            conn.execute(
                insert_sql,
                rows
            )

        total += len(rows)

        print(
            f"Loaded {total:,} rows"
        )


# ---------------------------------
# MAIN ETL
# ---------------------------------

def main():

    start = time.perf_counter()
    
    truncate_stock_data(engine)
    
    tickers = get_tickers(
        engine
    )
    stock_lookup = get_stock_lookup(
        engine
    )

    print(
        f"Tickers: {len(tickers)}"
    )

    for i in range(
        0,
        len(tickers),
        DOWNLOAD_BATCH_SIZE
    ):

        batch = tickers[
            i:i+DOWNLOAD_BATCH_SIZE
        ]

        print(
            f"Batch {(i//DOWNLOAD_BATCH_SIZE)+1}"
        )

        raw_df = download_batch(
            batch,
            START_DATE
        )

        if raw_df.empty:
            continue
        transformed = transform_stock_data(
            raw_df,
            stock_lookup
        )

        load_dataframe_to_sql(
            transformed,
            "stock_data",
            engine,
            LOAD_CHUNK_SIZE
        )

        time.sleep(
            PAUSE_SECONDS
        )

    end = time.perf_counter()
    print(
        f"Runtime: {end-start:.2f} sec"
    )

if __name__ == "__main__":
    main()
