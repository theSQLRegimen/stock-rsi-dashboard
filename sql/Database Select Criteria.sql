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
	((sd.price_close - sd.week_52_high)/sd.week_52_high)* 100 as dippct 
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
order by rsi, 'Net Margin' asc
