select artifact_id, count(*) as hops
from {{ ref('fct_artifact_flows') }}
group by 1
order by 2 desc
