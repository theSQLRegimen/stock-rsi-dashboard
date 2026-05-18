import pandas as pd
from sqlalchemy import create_engine, text


# ---------------------------------
# CONFIG
# ---------------------------------

engine = create_engine(
    "mssql+pyodbc://@localhost\\SQLEXPRESS/optionsregimen"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)



def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    # Add browser-like headers
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    df = pd.read_html(
        url,
        storage_options=headers
    )[0]

    tickers = [
        t.replace(".", "-")
        for t in df["Symbol"].tolist()
    ]

    return tickers


def update_sp500_flag(engine, tickers):
    """
    Updates stocks_master.sp500_flag
    1 = in S&P 500
    0 = not in S&P 500
    """

    if not tickers:
        raise ValueError("Ticker list is empty")

    # Convert for SQL IN clause
    placeholders = ", ".join(
        f":t{i}" for i in range(len(tickers))
    )

    params = {
        f"t{i}": ticker
        for i, ticker in enumerate(tickers)
    }

    with engine.begin() as conn:

        # Reset all flags
        conn.execute(text("""
            UPDATE stocks_master
            SET sp500_flag = 0
        """))

        # Set S&P members to 1
        sql = f"""
            UPDATE stocks_master
            SET sp500_flag = 1
            WHERE ticker IN ({placeholders})
        """

        result = conn.execute(
            text(sql),
            params
        )

        print(f"{result.rowcount} rows updated")
        
        
def main():    
    sp500_tickers = get_sp500_tickers()
    
    update_sp500_flag(
        engine,
        sp500_tickers
    )
    
    print("Update Operation Complete")
       
    
if __name__ == "__main__":
    main()
