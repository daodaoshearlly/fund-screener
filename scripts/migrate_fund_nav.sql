-- ============================================================
-- fund_nav 表优化脚本
-- 执行前请备份数据库！
-- ============================================================

-- 1. 添加复合索引（如果还没有）
-- 注意：如果表很大，这可能需要较长时间
ALTER TABLE fund_nav ADD INDEX idx_fund_nav_code_date (fund_code, nav_date);

-- ============================================================
-- 2. 分区表迁移（MariaDB）
-- ============================================================
-- 由于 MariaDB 不支持直接对已有数据的大表进行分区，
-- 需要按以下步骤操作：

-- 步骤 2.1：创建分区表结构
CREATE TABLE fund_nav_partitioned (
    id INT NOT NULL AUTO_INCREMENT,
    fund_code VARCHAR(10) NOT NULL,
    nav_date DATE NOT NULL,
    nav FLOAT,
    accumulated_nav FLOAT,
    daily_return FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, nav_date),
    INDEX idx_fund_code (fund_code),
    INDEX idx_fund_code_date (fund_code, nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(nav_date)) (
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- 步骤 2.2：复制数据（按日期范围分批插入，避免锁表）
-- 插入历史数据
INSERT INTO fund_nav_partitioned (id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at)
SELECT id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at
FROM fund_nav WHERE nav_date < '2023-01-01';

INSERT INTO fund_nav_partitioned (id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at)
SELECT id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at
FROM fund_nav WHERE nav_date >= '2023-01-01' AND nav_date < '2024-01-01';

INSERT INTO fund_nav_partitioned (id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at)
SELECT id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at
FROM fund_nav WHERE nav_date >= '2024-01-01' AND nav_date < '2025-01-01';

INSERT INTO fund_nav_partitioned (id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at)
SELECT id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at
FROM fund_nav WHERE nav_date >= '2025-01-01' AND nav_date < '2026-01-01';

-- 插入最新数据（当前年份）
INSERT INTO fund_nav_partitioned (id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at)
SELECT id, fund_code, nav_date, nav, accumulated_nav, daily_return, created_at
FROM fund_nav WHERE nav_date >= '2026-01-01';

-- 步骤 2.3：重命名表
RENAME TABLE fund_nav TO fund_nav_old;
RENAME TABLE fund_nav_partitioned TO fund_nav;

-- 步骤 2.4：验证数据一致性
SELECT COUNT(*) as original_count FROM fund_nav_old;
SELECT COUNT(*) as new_count FROM fund_nav;

-- 步骤 2.5：确认无误后删除旧表
-- DROP TABLE fund_nav_old;

-- ============================================================
-- 3. 定期维护：添加新分区（每年执行）
-- ============================================================
-- 在每年年初添加新分区
-- ALTER TABLE fund_nav ADD PARTITION (
--     PARTITION p2027 VALUES LESS THAN (2028)
-- );

-- ============================================================
-- 4. 查询优化验证
-- ============================================================
-- 查看索引使用情况
SHOW INDEX FROM fund_nav;

-- 查看分区信息
SELECT 
    PARTITION_NAME,
    PARTITION_ORDINAL_POSITION,
    TABLE_ROWS
FROM INFORMATION_SCHEMA.PARTITIONS
WHERE TABLE_SCHEMA = 'fund_screener' AND TABLE_NAME = 'fund_nav';
