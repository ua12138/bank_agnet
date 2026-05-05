-- 02_incident_aggregation.sql
-- Build incident windows and merge correlated alerts.

CREATE TEMPORARY VIEW alert_enriched AS
SELECT
    event_id,
    source,
    host,
    service,
    system,
    metric,
    `value`,
    severity,
    `timestamp`,
    message
FROM zabbix_alert_source;

CREATE TEMPORARY VIEW incident_windowed AS
SELECT
    CONCAT(
        'inc_',
        DATE_FORMAT(window_start, 'yyyyMMddHHmmss'),
        '_',
        system,
        '_',
        service
    ) AS incident_id,
    system,
    service,
    MAX(severity) AS severity,
    COUNT(*) AS event_count,
    window_start,
    window_end,
    COLLECT(host) AS hosts,
    COLLECT(metric) AS metrics,
    COLLECT(event_id) AS event_ids
FROM TABLE(
    TUMBLE(TABLE alert_enriched, DESCRIPTOR(`timestamp`), INTERVAL '5' MINUTE)
)
GROUP BY system, service, window_start, window_end;

