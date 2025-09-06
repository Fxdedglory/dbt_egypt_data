{% macro cf_text(expr) -%}
( {{ expr }} || '' )
{%- endmacro %}

{% macro cf_num(expr) -%}
( ( {{ expr }} ) * 1 )
{%- endmacro %}
