with src as (
  select * from {{ ref('sources') }}
)
select
  {{ cf_text('source_id') }}    as source_id,
  {{ cf_text('type') }}         as type,
  {{ cf_text('title') }}        as title,
  {{ cf_num('year') }}          as year,
  {{ cf_text('url_or_ref') }}   as url_or_ref,
  {{ cf_text('access') }}       as access,
  {{ cf_text('notes') }}        as notes,

  -- derived
  {{ cf_text("title || ' (' || cast(year as varchar) || ')'") }} as title_year,
  case when lower(access) in ('open','public') then 'open' else 'restricted' end as access_norm
from src
