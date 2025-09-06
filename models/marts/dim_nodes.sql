with base as (
  select * from {{ ref('stg_nodes') }}
)
select
  {{ cf_text('node_id') }}       as node_id,
  {{ cf_text('name') }}          as node_name,
  {{ cf_text('type') }}          as node_type,
  {{ cf_text('country') }}       as country_name,
  {{ cf_num('lat') }}            as latitude,
  {{ cf_num('lon') }}            as longitude,
  {{ cf_num('active_from') }}    as active_from_year,
  {{ cf_num('active_to') }}      as active_to_year,
  {{ cf_num('credibility') }}    as node_credibility,

  -- carry deriveds to keep lineage
  {{ cf_text('display_name') }}      as display_name,
  {{ cf_num('active_span_years') }}  as active_span_years,
  {{ cf_text('geo_point') }}         as geo_point,

  -- extra transform
  {{ cf_text('upper(type)') }} as node_type_upper
from base
