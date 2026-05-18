USE master;
GO

IF DB_ID('optionsregimen') IS NOT NULL
    DROP DATABASE optionsregimen;
GO

CREATE DATABASE optionsregimen;
GO

USE optionsregimen;
GO

-- Table: stocks
IF OBJECT_ID(N'dbo.stocks_master', N'U') IS NOT NULL
    DROP TABLE dbo.stocks_master;
GO

CREATE TABLE dbo.stocks_master (
    stock_id INT IDENTITY(1,1) PRIMARY KEY,              -- PK
    ticker NVARCHAR(16) NOT NULL,
    ticker_name NVARCHAR(255) NULL,
    ticker_description NVARCHAR(MAX) NULL,
    ticker_sector NVARCHAR(128) NULL,
    sp500_flag BIT NOT NULL DEFAULT(0)             -- s&p500_fl from diagram
	
	CONSTRAINT UQ_stocks_ticker UNIQUE (ticker)
);
GO

-- Table: stock_data
IF OBJECT_ID(N'dbo.stock_data', N'U') IS NOT NULL
    DROP TABLE dbo.stock_data;
GO

CREATE TABLE dbo.stock_data (
    stock_id INT NOT NULL,                          -- FK -> stocks.stockid
    price_date DATE NOT NULL,
    price_close DECIMAL(18,4) NULL,
    price_high DECIMAL(18,4) NULL,
    price_low DECIMAL(18,4) NULL,
    rsi DECIMAL(6,2) NULL,
    week_52_high DECIMAL(18,4) NULL,               -- renamed 52week_high
    CONSTRAINT PK_stock_data PRIMARY KEY (stock_id, price_date),
	
    CONSTRAINT FK_stock_data_stocks FOREIGN KEY (stock_id)
        REFERENCES dbo.stocks_master(stock_id)

);

GO
-- Table: stock_income_data
IF OBJECT_ID(N'dbo.stock_income_data', N'U') IS NOT NULL
    DROP TABLE dbo.stock_income_data;
GO

CREATE TABLE dbo.stock_income_data (
    id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    stock_id INT NOT NULL,                         -- FK -> stocks.stockid
    period_type NVARCHAR(32) NOT NULL,             -- e.g., 'quarter', 'annual'
    period_end DATE NOT NULL,
    revenue DECIMAL(20,2) NULL,
    net_income DECIMAL(20,2) NULL,

    CONSTRAINT UQ_stock_income_stock_period UNIQUE (stock_id, period_type, period_end),
	
    CONSTRAINT FK_stock_income_stocks FOREIGN KEY (stock_id)
        REFERENCES dbo.stocks_master(stock_id)
);
GO

