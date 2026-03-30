CREATE DATABASE IF NOT EXISTS `weather`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `weather`;

-- weather_observations: raw per-minute sensor readings from the Tempest station
CREATE TABLE IF NOT EXISTS `weather_observations` (
  `id`                                   CHAR(36)          NOT NULL                 COMMENT 'SHA-256 UUID derived from station_id + timestamp',
  `station_id`                           INT UNSIGNED      NOT NULL                 COMMENT 'Tempest station identifier',
  `timestamp`                            BIGINT            NOT NULL                 COMMENT 'Unix epoch seconds (UTC)',
  `conditions`                           VARCHAR(64)       DEFAULT NULL             COMMENT 'Text weather description - populated at top of hour from better_forecast',
  `icon`                                 VARCHAR(64)       DEFAULT NULL             COMMENT 'Icon identifier - populated at top of hour from better_forecast',
  `air_temperature`                      DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius',
  `relative_humidity`                    INT               DEFAULT NULL             COMMENT 'Percent (%)',
  `dew_point`                            DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius',
  `wet_bulb_temperature`                 DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius',
  `wet_bulb_globe_temperature`           DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius - heat stress index',
  `delta_t`                              DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius - difference between air temp and wet bulb',
  `feels_like`                           DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius - apparent temperature',
  `heat_index`                           DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius',
  `wind_chill`                           DECIMAL(6,2)      DEFAULT NULL             COMMENT 'Degrees Celsius',
  `barometric_pressure`                  DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mbar (hPa) - raw sensor pressure',
  `station_pressure`                     DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mbar (hPa) - corrected to station elevation',
  `sea_level_pressure`                   DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mbar (hPa) - corrected to sea level',
  `pressure_trend`                       VARCHAR(20)       DEFAULT NULL             COMMENT 'rising, falling, or steady',
  `wind_avg`                             DECIMAL(6,2)      DEFAULT NULL             COMMENT 'm/s - 1-minute average',
  `wind_gust`                            DECIMAL(6,2)      DEFAULT NULL             COMMENT 'm/s - highest 3-second sample in the minute',
  `wind_lull`                            DECIMAL(6,2)      DEFAULT NULL             COMMENT 'm/s - lowest 3-second sample in the minute',
  `wind_direction`                       INT               DEFAULT NULL             COMMENT 'Degrees (0-360)',
  `wind_direction_cardinal`              CHAR(3)           DEFAULT NULL             COMMENT 'Cardinal wind direction - populated at top of hour from better_forecast',
  `precip`                               DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mm - precipitation in the last minute',
  `precip_accum_last_1hr`                DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mm - rolling 1-hour accumulation',
  `precip_accum_local_day`               DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mm - accumulation since local midnight',
  `precip_accum_local_day_final`         DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mm - rain-check corrected daily accumulation',
  `precip_accum_local_yesterday`         DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mm - yesterdays raw accumulation',
  `precip_accum_local_yesterday_final`   DECIMAL(8,4)      DEFAULT NULL             COMMENT 'mm - yesterdays rain-check corrected accumulation',
  `precip_analysis_type_yesterday`       INT               DEFAULT NULL             COMMENT '0=none, 1=rain check passed, 2=rain check failed',
  `precip_minutes_local_day`             INT               DEFAULT NULL             COMMENT 'Minutes of precipitation today',
  `precip_minutes_local_yesterday`       INT               DEFAULT NULL             COMMENT 'Minutes of precipitation yesterday (raw)',
  `precip_minutes_local_yesterday_final` INT               DEFAULT NULL             COMMENT 'Minutes of precipitation yesterday (rain-check corrected)',
  `solar_radiation`                      INT               DEFAULT NULL             COMMENT 'W/m²',
  `uv`                                   DECIMAL(5,2)      DEFAULT NULL             COMMENT 'UV index (dimensionless)',
  `brightness`                           INT               DEFAULT NULL             COMMENT 'Lux',
  `lightning_strike_count`               INT               DEFAULT NULL             COMMENT 'Strikes detected in the last minute',
  `lightning_strike_count_last_1hr`      INT               DEFAULT NULL             COMMENT 'Strikes detected in the last hour',
  `lightning_strike_count_last_3hr`      INT               DEFAULT NULL             COMMENT 'Strikes detected in the last 3 hours',
  `lightning_strike_last_distance`       INT               DEFAULT NULL             COMMENT 'km - distance to last detected strike',
  `air_density`                          DECIMAL(7,4)      DEFAULT NULL             COMMENT 'kg/m³',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_station_timestamp` (`station_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- weather_forecast_hourly: hourly forecast snapshots (appended each poll, never overwritten)
CREATE TABLE IF NOT EXISTS `weather_forecast_hourly` (
  `id`                  CHAR(36)          NOT NULL COMMENT 'SHA-256 UUID derived from station_id + fetched_at + forecast_time',
  `station_id`          INT UNSIGNED      NOT NULL COMMENT 'Tempest station identifier',
  `fetched_at`          BIGINT            NOT NULL COMMENT 'Unix epoch when forecast was retrieved',
  `forecast_time`       BIGINT            NOT NULL COMMENT 'Unix epoch of the forecast hour',
  `conditions`          VARCHAR(64)       DEFAULT NULL COMMENT 'Text weather description',
  `icon`                VARCHAR(64)       DEFAULT NULL COMMENT 'Icon identifier',
  `air_temperature`     DECIMAL(6,2)      DEFAULT NULL COMMENT 'Degrees Celsius',
  `feels_like`          DECIMAL(6,2)      DEFAULT NULL COMMENT 'Degrees Celsius - apparent temperature',
  `wind_avg`            DECIMAL(6,2)      DEFAULT NULL COMMENT 'm/s',
  `wind_direction`      SMALLINT UNSIGNED DEFAULT NULL COMMENT 'Degrees (0-360)',
  `wind_direction_cardinal` CHAR(3)       DEFAULT NULL COMMENT 'Cardinal wind direction',
  `precip_probability`  TINYINT UNSIGNED  DEFAULT NULL COMMENT 'Percent chance of precipitation (0-100)',
  `precip`              DECIMAL(8,4)      DEFAULT NULL COMMENT 'mm - forecasted precipitation for this hour',
  `precip_type`         VARCHAR(20)       DEFAULT NULL COMMENT 'rain, snow, sleet, storm, or mix',
  `relative_humidity`   INT               DEFAULT NULL COMMENT 'Percent (%)',
  `uv`                  DECIMAL(5,2)      DEFAULT NULL COMMENT 'UV index (dimensionless)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_station_fetch_hour` (`station_id`, `fetched_at`, `forecast_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- weather_forecast_daily: daily forecast snapshots (appended each poll, never overwritten)
CREATE TABLE IF NOT EXISTS `weather_forecast_daily` (
  `id`                  CHAR(36)          NOT NULL COMMENT 'SHA-256 UUID derived from station_id + fetched_at + day_start_local',
  `station_id`          INT UNSIGNED      NOT NULL COMMENT 'Tempest station identifier',
  `fetched_at`          BIGINT            NOT NULL COMMENT 'Unix epoch when forecast was retrieved',
  `day_start_local`     BIGINT            NOT NULL COMMENT 'Unix epoch of local midnight for the forecast day',
  `conditions`          VARCHAR(64)       DEFAULT NULL COMMENT 'Text weather description',
  `icon`                VARCHAR(64)       DEFAULT NULL COMMENT 'Icon identifier',
  `air_temp_high`       DECIMAL(6,2)      DEFAULT NULL COMMENT 'Degrees Celsius - forecast high',
  `air_temp_low`        DECIMAL(6,2)      DEFAULT NULL COMMENT 'Degrees Celsius - forecast low',
  `precip_probability`  TINYINT UNSIGNED  DEFAULT NULL COMMENT 'Percent chance of precipitation (0-100)',
  `precip_type`         VARCHAR(20)       DEFAULT NULL COMMENT 'rain, snow, sleet, storm, or mix',
  `sunrise`             BIGINT            DEFAULT NULL COMMENT 'Unix epoch of local sunrise',
  `sunset`              BIGINT            DEFAULT NULL COMMENT 'Unix epoch of local sunset',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_station_fetch_day` (`station_id`, `fetched_at`, `day_start_local`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;