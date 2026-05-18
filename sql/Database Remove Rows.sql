/*
truncate table stock_income_data;
truncate table stock_data;
delete from  stocks_master;
*/

select * from stock_data

select distinct stockid
into #bad_stocks
from (
    select stockid 
    from stock_data 
    where week_52_high is null 
      and price_date = '2026-04-20'

    union

    select stock_id
    from stock_income_data
    where (revenue = 0 or revenue is null or net_income is null or net_income = 0)
      and period_end = '2025-12-31'
      and period_type in ('annual', 'quarterly')
) x;

delete from stock_income_data
where stock_id in (select stockid from #bad_stocks);

delete from stock_data
where stockid in (select stockid from #bad_stocks);

delete from stocks_master
where stockid in (select stockid from #bad_stocks);

