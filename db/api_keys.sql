CREATE TABLE IF NOT EXISTS `api_keys` (
  `id`           CHAR(36)     NOT NULL                 COMMENT 'SHA-256 UUID derived from key_hash (first 32 hex chars, UUID-formatted)',
  `key_hash`     CHAR(64)     NOT NULL                 COMMENT 'SHA-256 hex digest of the full key (including prefix)',
  `label`        VARCHAR(255) NOT NULL,
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used_at` DATETIME     NULL,
  `expires_at`   DATETIME     NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_key_hash` (`key_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
