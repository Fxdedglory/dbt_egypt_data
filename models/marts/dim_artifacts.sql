with base as (
  select * from {{ ref('stg_artifacts') }}
)
select
  {{ cf_text('artifact_id') }}     as artifact_id,
  {{ cf_text('title') }}           as artifact_title,
  {{ cf_text('category') }}        as artifact_category,
  {{ cf_text('period') }}          as artifact_period,
  {{ cf_text('origin_node_id') }}  as origin_node_id,
  {{ cf_num('origin_date_start') }} as origin_date_start,
  {{ cf_num('origin_date_end') }}   as origin_date_end,
  {{ cf_text('material') }}        as artifact_material,
  {{ cf_text('status') }}          as artifact_status,
  {{ cf_text('visibility') }}      as artifact_visibility,
  {{ cf_num('credibility') }}      as artifact_credibility,

  -- carry/derive
  {{ cf_num('origin_span_years') }}     as origin_span_years,
  {{ cf_text('title_with_period') }}    as title_with_period,
  {{ cf_text('material_group') }}       as material_group,
  case when credibility >= 0.8 then 'high'
       when credibility >= 0.5 then 'medium'
       else 'low'
  end as credibility_bucket
from base
