with flows as (
  select * from {{ ref('fct_artifact_flows') }}
),
arts as (
  select artifact_id, artifact_title, artifact_period, artifact_status, credibility_bucket
  from {{ ref('dim_artifacts') }}
)
select
  {{ cf_text('a.artifact_id') }}      as artifact_id,
  {{ cf_text('a.artifact_title') }}   as artifact_title,
  {{ cf_text('a.artifact_period') }}  as artifact_period,
  {{ cf_text('a.artifact_status') }}  as artifact_status,
  {{ cf_text('a.credibility_bucket') }} as credibility_bucket,
  {{ cf_text('f.flow_id') }}          as flow_id,
  {{ cf_text('f.from_name') }}        as from_name,
  {{ cf_text('f.to_name') }}          as to_name,
  {{ cf_text('f.flow_type') }}        as flow_type,
  {{ cf_text('f.era') }}              as era,
  {{ cf_num('f.year_start') }}        as year_start,
  {{ cf_num('f.year_end') }}          as year_end,
  {{ cf_num('f.year_end - f.year_start') }} as hop_years,
  {{ cf_text("a.artifact_title || ' — ' || f.from_name || '→' || f.to_name") }} as journey_label
from arts a
left join flows f on f.artifact_id = a.artifact_id
order by a.artifact_id, f.year_start
