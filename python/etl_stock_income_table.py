# -*- coding: utf-8 -*-
"""
Stock Income ETL
Streaming extract -> transform -> load

Loads annual + quarterly income data
from Yahoo Finance into stock_income_data
"""

import time
import math
import pandas as pd
import yfinance as yf

from sqlalchemy import create_engine, text
import numpy as np


# --------------------------------
# CONFIG
# --------------------------------

engine = create_engine(
    "mssql+pyodbc://@localhost\\SQLEXPRESS/optionsregimen"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)

BATCH_SIZE = 25


# --------------------------------
# SOURCE TICKERS
# --------------------------------

def ticker_extract_db(engine):

    print("Pulling tickers...")

    df = pd.read_sql("""
        SELECT ticker
        FROM dbo.stocks_master
        WHERE ticker IS NOT NULL
        ORDER BY ticker
    """, engine)

    return df["ticker"].tolist()


def get_stock_lookup(engine):

    df = pd.read_sql("""
        SELECT stockid, ticker
        FROM dbo.stocks_master
    """, engine)

    return dict(
        zip(
            df["ticker"],
            df["stockid"]
        )
    )


# --------------------------------
# EXTRACT
# --------------------------------

def extract_stock_income_batch(
    ticker_batch
):

    results = []
    failed = []

    for ticker in ticker_batch:

        try:

            t = yf.Ticker(
                ticker
            )

            results.append({
                "ticker": ticker,
                "annual": t.financials,
                "quarterly": t.quarterly_financials
            })

        except Exception as e:

            print(
               f"{ticker} failed: {e}"
            )

            failed.append(
                ticker
            )

    return results, failed


# --------------------------------
# TRANSFORM
# --------------------------------

def transform_income_data(
    raw_data,
    stock_lookup
):

    all_data=[]

    for item in raw_data:

        ticker=item["ticker"]

        stock_id=stock_lookup.get(
            ticker
        )

        if stock_id is None:
            continue


        for df,period_type in [
            (
                item["annual"],
                "annual"
            ),
            (
                item["quarterly"],
                "quarterly"
            )
        ]:

            if (
                df is None
                or df.empty
            ):
                continue


            temp=(
                df.T
                .reset_index()
                .rename(
                    columns={
                        "index":"period_end"
                    }
                )
            )


            temp["revenue"]=temp.get(
                "Total Revenue"
            )

            temp["net_income"]=temp.get(
                "Net Income"
            )


            # FIXED NAME
            temp["stock_id"]=stock_id

            temp["ticker"]=ticker

            temp["period_type"]=period_type


            temp=temp[
                [
                    "stock_id",
                    "ticker",
                    "period_type",
                    "period_end",
                    "revenue",
                    "net_income"
                ]
            ]


            all_data.append(
                temp
            )


    if not all_data:
        return pd.DataFrame()


    df = pd.concat(
        all_data,
        ignore_index=True
    )


    df = df.drop_duplicates(
        subset=[
            "stock_id",
            "period_type",
            "period_end"
        ]
    )


    # SQL-safe date conversion
    df["period_end"] = pd.to_datetime(
        df["period_end"]
    ).dt.strftime(
        "%Y-%m-%d"
    )


    return df

# ---------------------------------
# Truncate
# ---------------------------------

def truncate_stock_data(engine):
    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE stock_income_data;"))
            conn.commit()
        print("Table stock_data truncated successfully.")
    except Exception as e:
        print(f"Error truncating table: {e}")


# --------------------------------
# LOAD
# --------------------------------

def load_dataframe_to_sql(
    df,
    table_name,
    engine
):

    if df.empty:
        return 0

    df = df.replace({np.nan: None})
    # defensive validation
    required = [
        "stock_id",
        "period_type",
        "period_end"
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )


    query="""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = :table_name
    """


    with engine.connect() as conn:

        result=conn.execute(
            text(query),
            {
                "table_name":
                table_name
            }
        )

        table_cols=[
            row[0]
            for row in result.fetchall()
        ]


    df_cols=[
        c for c in df.columns
        if c in table_cols
    ]


    if not df_cols:
        raise ValueError(
            "No matching columns between dataframe and SQL table."
        )


    col_str=", ".join(
        df_cols
    )

    placeholders=", ".join(
        [
            f":{c}"
            for c in df_cols
        ]
    )


    sql=text(f"""
        INSERT INTO dbo.{table_name}
        ({col_str})
        VALUES
        ({placeholders})
    """)


    rows=(
        df[df_cols]
        .to_dict(
            orient="records"
        )
    )


    with engine.begin() as conn:

        conn.execute(
            sql,
            rows
        )


    print(
      f"Loaded {len(rows):,} rows "
      f"into {table_name}"
    )

    return len(rows)


# --------------------------------
# ETL DRIVER
# --------------------------------

def load_stock_income_pipeline():

    tickers=ticker_extract_db(
        engine
    )

    stock_lookup=get_stock_lookup(
        engine
    )


    total_tickers=len(
        tickers
    )


    total_batches=math.ceil(
        total_tickers /
        BATCH_SIZE
    )


    completed=0
    total_rows=0
    failed_all=[]


    for i in range(
        0,
        total_tickers,
        BATCH_SIZE
    ):

        batch_num=(
            i // BATCH_SIZE
        ) + 1


        batch=tickers[
            i:i+BATCH_SIZE
        ]


        print(
            "\n"
            f"Batch "
            f"{batch_num}/"
            f"{total_batches}"
        )


        raw_data,failed=(
            extract_stock_income_batch(
                batch
            )
        )


        transformed=(
            transform_income_data(
                raw_data,
                stock_lookup
            )
        )


        rows_loaded=(
            load_dataframe_to_sql(
                transformed,
                "stock_income_data",
                engine
            )
        )


        total_rows += rows_loaded

        completed += len(
            batch
        )

        remaining=(
            total_tickers
            - completed
        )

        failed_all.extend(
            failed
        )


        pct=(
            completed /
            total_tickers
        ) * 100


        print(
            f"Completed "
            f"{completed:,}/"
            f"{total_tickers:,} "
            f"({pct:.1f}%)"
        )

        print(
            f"Tickers left: "
            f"{remaining:,}"
        )

        print(
            f"Rows loaded this batch: "
            f"{rows_loaded:,}"
        )

        print(
            f"Total rows loaded: "
            f"{total_rows:,}"
        )

        print(
            f"Failures so far: "
            f"{len(failed_all)}"
        )


    print("\nDONE")

    print(
        f"Total rows inserted: "
        f"{total_rows:,}"
    )


    if failed_all:

        print(
            "\nFailed tickers:"
        )

        print(
            failed_all
        )


# --------------------------------
# MAIN
# --------------------------------

def main():

    start=time.perf_counter()
    
    truncate_stock_data(engine)
    
    load_stock_income_pipeline()

    end=time.perf_counter()

    print(
        f"\nRuntime: "
        f"{end-start:.2f}s"
    )
 

if __name__=="__main__":
    main()