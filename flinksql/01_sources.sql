-- 01_sources.sql
-- Kafka source tables for Zabbix events and XueLang changes.

CREATE TABLE IF NOT EXISTS zabbix_alert_source (
    event_id STRING,
    source STRING,
    host STRING,
    service STRING,
    system STRING,
    metric STRING,
    `value` DOUBLE,
    severity STRING,
    `timestamp` TIMESTAMP(3),
    message STRING,
    WATERMARK FOR `timestamp` AS `timestamp` - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'zabbix-alert-topic',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-aiops-alert',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);

CREATE TABLE IF NOT EXISTS xuelang_change_source (
    change_id STRING,
    system STRING,
    service STRING,
    owner STRING,
    summary STRING,
    change_time TIMESTAMP(3),
    WATERMARK FOR change_time AS change_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'xuelang-change-topic',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-aiops-change',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);

