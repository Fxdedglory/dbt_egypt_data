with src as (
  select * from {{ ref('flows') }}
)
select
  {{ cf_text('flow_id') }}        as flow_id,
  {{ cf_text('artifact_id') }}    as artifact_id,
  {{ cf_text('from_node_id') }}   as from_node_id,
  {{ cf_text('to_node_id') }}     as to_node_id,
  {{ cf_num('year_start') }}      as year_start,
  {{ cf_num('year_end') }}        as year_end,
  {{ cf_text('flow_type') }}      as flow_type,
  {{ cf_text('era') }}            as era,

  -- derived
  {{ cf_num('year_end - year_start') }}    as duration_years,
  {{ cf_text("from_node_id || '→' || to_node_id") }} as route_key
from src
