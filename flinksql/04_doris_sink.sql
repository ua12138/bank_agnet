-- 04_doris_sink.sql
-- Persist incident aggregation into Doris for historical analytics.

CREATE TABLE IF NOT EXISTS doris_incident_sink (
    incident_id STRING,
    system_name STRING,
    service_name STRING,
    severity STRING,
    event_count BIGINT,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    hosts STRING,
    metrics STRING
) WITH (
    'connector' = 'doris',
    'fenodes' = 'doris-fe:8030',
    'table.identifier' = 'aiops.incident_agg',
    'username' = 'root',
    'password' = ''
);

INSERT INTO doris_incident_sink
SELECT
    incident_id,
    system,
    service,
    severity,
    event_count,
    window_start,
    window_end,
    ARRAY_TO_STRING(hosts, ',') AS hosts,
    ARRAY_TO_STRING(metrics, ',') AS metrics
FROM incident_windowed;

