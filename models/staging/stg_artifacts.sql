with src as (
  select * from {{ ref('artifacts') }}
)
select
  {{ cf_text('artifact_id') }}       as artifact_id,
  {{ cf_text('title') }}             as title,
  {{ cf_text('category') }}          as category,
  {{ cf_text('period') }}            as period,
  {{ cf_text('origin_node_id') }}    as origin_node_id,
  {{ cf_num('origin_date_start') }}  as origin_date_start,
  {{ cf_num('origin_date_end') }}    as origin_date_end,
  {{ cf_text('material') }}          as material,
  {{ cf_text('status') }}            as status,
  {{ cf_text('visibility') }}        as visibility,
  {{ cf_num('credibility') }}        as credibility,

  -- derived
  {{ cf_num('origin_date_end - origin_date_start') }} as origin_span_years,
  {{ cf_text("title || ' [' || period || ']'") }}     as title_with_period,
  case
    when lower(material) like '%stone%' then 'stone'
    when lower(material) like '%wood%'  then 'wood'
    when lower(material) like '%metal%' then 'metal'
    else 'other'
  end as material_group
from src
