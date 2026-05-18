


UPDATE stocks_master
SET ticker_sector = 'Uncategorized'
WHERE ticker_sector IS NULL
   OR ticker_sector = '';