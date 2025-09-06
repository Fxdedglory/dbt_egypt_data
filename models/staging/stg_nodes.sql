with src as (
  select * from {{ ref('nodes') }}
)
select
  {{ cf_text("node_id") }}     as node_id,
  {{ cf_text("name") }}        as name,
  {{ cf_text("type") }}        as type,
  {{ cf_text("country") }}     as country,
  {{ cf_num("lat") }}          as lat,
  {{ cf_num("lon") }}          as lon,
  {{ cf_num("active_from") }}  as active_from,
  {{ cf_num("active_to") }}    as active_to,
  {{ cf_num("credibility") }}  as credibility,
  {{ cf_text("notes") }}       as notes,

  -- derived (real transforms so colibri sees lineage)
  {{ cf_text("name || ' (' || country || ')'") }} as display_name,
  {{ cf_num("active_to - active_from") }}         as active_span_years,

  -- use CONCAT to avoid nested quotes with ||
  {{ cf_text("concat(cast(lat as varchar), ',', cast(lon as varchar))") }} as geo_point
from src
