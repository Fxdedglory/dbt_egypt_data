with f as (
  select * from {{ ref('stg_flows') }}
),
-- select the correct column names exposed by dim_nodes
n as (
  select
    node_id,
    node_name,
    country_name
  from {{ ref('dim_nodes') }}
)
select
  {{ cf_text('f.flow_id') }}       as flow_id,
  {{ cf_text('f.artifact_id') }}   as artifact_id,

  {{ cf_text('f.from_node_id') }}  as from_node_id,
  {{ cf_text('fn.node_name') }}    as from_name,

  {{ cf_text('f.to_node_id') }}    as to_node_id,
  {{ cf_text('tn.node_name') }}    as to_name,

  {{ cf_text('f.flow_type') }}     as flow_type,
  {{ cf_text('f.era') }}           as era,
  {{ cf_num('f.year_start') }}     as year_start,
  {{ cf_num('f.year_end') }}       as year_end,
  {{ cf_num('f.duration_years') }} as duration_years,
  {{ cf_text('f.route_key') }}     as route_key,

  {{ cf_text("fn.country_name || '→' || tn.country_name") }} as route_countries
from f
left join n fn on fn.node_id = f.from_node_id
left join n tn on tn.node_id = f.to_node_id
