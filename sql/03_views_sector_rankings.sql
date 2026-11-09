SELECT SCHEMA_NAME(schema_id) AS schema_name, name AS table_name
FROM sys.tables
WHERE name NOT IN (
    'MSreplication_options',
    'spt_fallback_db',
    'spt_fallback_dev',
    'spt_fallback_usg',
    'spt_monitor'
)
ORDER BY schema_name, table_name;
