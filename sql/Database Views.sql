
DROP VIEW IF EXISTS dbo.vw_stock_screen;
go
CREATE VIEW dbo.vw_stock_screen AS
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
	sd.price_close - sd.week_52_high as dip,
	((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 as dippct,
	case when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -10 and -5 then 'Normal Pullback'
		 when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -20 and -10  then 'Correction'
         when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -35 and -20  then 'Deep Correction'
	              when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -50 and -30  then 'Bear-market drawdown'
		 when ((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -70 and -50   then 'Crash / severe dislocation' 
		 when((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -80 and -70  then 'Potential “broken stock” territory recovery unlikely'
		  when((sd.price_close - sd.week_52_high)/sd.week_52_high) * 100 between -100 and -80  then 'The Fallen Knife'
    else 'UnCategorized'  END as Dip_Interpretation

from stocks_master sm
join stock_data sd on sd.stockid = sm.stockid
left join stock_income_data sind on sm.stockid = sind.stock_id
where period_type = 'annual' and sind.net_income is not null and sind.revenue is not null 
and revenue <> 0 and sd.price_date = CAST(GETDATE() AS DATE)
and sind.period_end = '2025-12-31'  -- and (revenue = 0 or revenue is null or net_income is null or net_income = 0)
and price_close > 5 --no penny stocks  
and case 
    when  (sind.net_income/sind.revenue) * 100 < 0 then 'Not Profitable'
    else 'Profitable'
	end  = 'Profitable'




go


DROP VIEW IF EXISTS dbo.vw_stock_income_data_annual;
go
CREATE VIEW dbo.vw_stock_income_data_annual AS

select stock_id, sm.ticker, FORMAT(period_end, 'yyyy') year_earnings, revenue, net_income from stock_income_data sd
join stocks_master sm on sm.stockid = sd.stock_id
where period_type = 'annual' and FORMAT(period_end, 'yyyy') <> 2021

