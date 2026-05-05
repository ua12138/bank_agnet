-- 03_task_sink_postgres.sql
-- Sink incident into PostgreSQL diagnosis_task table.

CREATE TABLE IF NOT EXISTS diagnosis_task_sink (
    incident_id STRING,
    system_name STRING,
    service_name STRING,
    priority STRING,
    status STRING,
    payload_json STRING,
    retry_count INT,
    max_retry INT,
    need_notify BOOLEAN,
    notify_status STRING,
    created_at TIMESTAMP(3),
    updated_at TIMESTAMP(3),
    PRIMARY KEY (incident_id) NOT ENFORCED
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://postgres:5432/aiops',
    'table-name' = 'diagnosis_task',
    'driver' = 'org.postgresql.Driver',
    'username' = 'aiops',
    'password' = 'aiops'
);

INSERT INTO diagnosis_task_sink
SELECT
    incident_id,
    system AS system_name,
    service AS service_name,
    CASE
        WHEN severity = 'critical' THEN 'P0'
        WHEN severity = 'high' THEN 'P1'
        ELSE 'P2'
    END AS priority,
    'NEW' AS status,
    TO_JSON(
        MAP[
            'incident_id', incident_id,
            'system', system,
            'service', service,
            'severity', severity,
            'event_count', CAST(event_count AS STRING),
            'window_start', CAST(window_start AS STRING),
            'window_end', CAST(window_end AS STRING)
        ]
    ) AS payload_json,
    0 AS retry_count,
    3 AS max_retry,
    TRUE AS need_notify,
    'PENDING' AS notify_status,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
FROM incident_windowed;

