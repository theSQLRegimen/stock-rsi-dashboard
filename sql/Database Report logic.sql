
    -- Your query definition here
    select  ticker,
	ticker_name, 
	ticker_sector,
	sd.price_date, 
	sd.price_close,
	sd.week_52_high,
	sd.rsi as 'RSI',
	case when rsi between 0 and 20 then 'Extremely Oversold'
		 when rsi between 20 and 30 then 'Oversold'
         when rsi between 30 and 70 then 'Neutral'
	     when rsi between 70 and 80 then 'Overbrought' 
		 when rsi between 80 and 100 then 'Extremely Overbrought'
    else 'Unknown'  END as 'RSI Level Description',
	sind.period_type,
	sind.period_end,
	sind.revenue,
	sind.net_income,
	sind.revenue / 1000000000.0 AS 'Revenue Billions',
	sind.net_income/ 1000000000.0 as'Net Income Billions',
	concat(cast((sind.net_income/sind.revenue) * 100 as decimal(10,2)), '%')  as 'Net Margin',
	case 
    when  (sind.net_income/sind.revenue) * 100 < 0 then 'Not Profitable'
    else 'Profitable'
	end as 'Profitablity',
	sd.price_close - sd.week_52_high  as dip,
	((sd.price_close - sd.week_52_high)/sd.week_52_high)* 100 as dippct, 
	case when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -10 and -5 then 'Normal Pullback'
		 when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -20 and -11  then 'Correction'
         when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -35 and -21  then 'Deep Correction'
	              when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -50 and -36  then 'Bear-market drawdown'
		 when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -70 and -51   then 'Crash / severe dislocation' 
		 when((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -80 and -71  then 'Potential “broken stock” territory recovery unlikely'
		  when((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -100 and -81  then 'The Fallen Knife'
    else 'UnCategorized'  END as RSI_Interuption
into #core_results
from stocks_master sm
join stock_data sd on sd.stockid = sm.stockid
left join stock_income_data sind on sm.stockid = sind.stock_id
where price_date = '2026-04-20' and period_type = 'annual' and
sind.period_end = '2025-12-31'  -- and (revenue = 0 or revenue is null or net_income is null or net_income = 0)
and price_close > 5 --no penny stocks 
and case 
    when  (sind.net_income/sind.revenue) * 100 < 0 then 'Not Profitable'
    else 'Profitable'
	end  = 'Profitable'


-- Main query referencing the CTE
SELECT count (ticker) as 'rsi under 30' FROM #core_results
where rsi < 30

SELECT count (ticker) as 'rsi to watch 30 - 40' FROM #core_results
where rsi between 30 and 35

-- fits criteria rsi, profitablity, 
select price_date, ticker, 
ticker_name,
price_close,
rsi, concat(cast((net_income/revenue) * 100 as decimal(10,2)), '%')  as 'Net Margin',
((price_close - week_52_high)/week_52_high)* 100 as dippct
FROM #core_results
where rsi < 30
order by cast((net_income/revenue) * 100 as decimal(10,2)) desc


-- approaching criteria rsi, profitablity, 
select price_date, ticker, 
ticker_name,
price_close,
rsi, concat(cast((net_income/revenue) * 100 as decimal(10,2)), '%')  as 'Net Margin',
((price_close - week_52_high)/week_52_high)* 100 as dippct
FROM #core_results
where rsi between 30 and 35
order by cast((net_income/revenue) * 100 as decimal(10,2)) desc


-- industry with rsi < 35
select ticker_sector,  count (ticker_sector) Count_Breakdown from #core_results
where rsi <= 35
group by ticker_sector 
order by Count_Breakdown desc

-- Biggest dip with rsi < 35

SELECT TOP 1 ticker,
    ticker_name, 
	price_close,
    ((price_close - week_52_high) / week_52_high * 100) AS pct_below_52w_high, 
	RSI_Interuption
FROM #core_results
WHERE rsi <= 35
ORDER BY pct_below_52w_high ASC; 



select avg(sd.rsi)
from stocks_master sm
join stock_data sd on sd.stockid = sm.stockid
where price_date = '2026-05-07'