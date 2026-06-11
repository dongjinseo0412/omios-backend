-- OMIOS MySQL schema
-- Charset is set to utf8mb4 so Korean and Japanese text are stored safely.

CREATE DATABASE IF NOT EXISTS omios
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE omios;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS product_purchase_locations;
DROP TABLE IF EXISTS product_links;
DROP TABLE IF EXISTS product_like_counts;
DROP TABLE IF EXISTS product_likes;
DROP TABLE IF EXISTS product_keywords;
DROP TABLE IF EXISTS product_age_groups;
DROP TABLE IF EXISTS product_targets;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS purchase_locations;
DROP TABLE IF EXISTS keywords;
DROP TABLE IF EXISTS age_groups;
DROP TABLE IF EXISTS gift_targets;
DROP TABLE IF EXISTS price_ranges;
DROP TABLE IF EXISTS regions;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE regions (
    region_code VARCHAR(20) PRIMARY KEY,
    name_ko VARCHAR(100) NOT NULL,
    name_jp VARCHAR(100),
    parent_region_code VARCHAR(20),
    description TEXT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT,
    CONSTRAINT fk_regions_parent
        FOREIGN KEY (parent_region_code) REFERENCES regions(region_code)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE price_ranges (
    price_range_code VARCHAR(20) PRIMARY KEY,
    label VARCHAR(100) NOT NULL,
    min_price INT NOT NULL,
    max_price INT,
    sort_order INT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE gift_targets (
    target_code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE age_groups (
    age_group_code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    min_age INT,
    max_age INT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE keywords (
    keyword_code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT,
    INDEX idx_keywords_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE purchase_locations (
    location_code VARCHAR(20) PRIMARY KEY,
    region_code VARCHAR(20),
    name VARCHAR(255) NOT NULL,
    location_type VARCHAR(100),
    description TEXT,
    address TEXT,
    website_url TEXT,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT,
    CONSTRAINT fk_purchase_locations_region
        FOREIGN KEY (region_code) REFERENCES regions(region_code)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    INDEX idx_purchase_locations_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE products (
    product_code VARCHAR(20) PRIMARY KEY,
    name_ko VARCHAR(255) NOT NULL,
    name_jp VARCHAR(255),
    brand_name VARCHAR(255),
    primary_region_code VARCHAR(20) NOT NULL,
    price_range_code VARCHAR(20) NOT NULL,
    price INT,
    description TEXT,
    purchase_tip TEXT,
    is_region_limited TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    image_url TEXT,
    source_note TEXT,
    collector VARCHAR(100),
    collected_date DATE,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_region
        FOREIGN KEY (primary_region_code) REFERENCES regions(region_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_products_price_range
        FOREIGN KEY (price_range_code) REFERENCES price_ranges(price_range_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_products_region (primary_region_code),
    INDEX idx_products_price (price),
    INDEX idx_products_price_range (price_range_code),
    INDEX idx_products_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_likes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_likes_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    UNIQUE KEY uq_product_likes_product_client (product_code, client_id),
    INDEX idx_product_likes_product (product_code),
    INDEX idx_product_likes_client (client_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_like_counts (
    product_code VARCHAR(20) PRIMARY KEY,
    like_count INT NOT NULL DEFAULT 0,
    refreshed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_like_counts_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_product_like_counts_count (like_count),
    INDEX idx_product_like_counts_refreshed_at (refreshed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_targets (
    product_code VARCHAR(20) NOT NULL,
    target_code VARCHAR(20) NOT NULL,
    note TEXT,
    PRIMARY KEY (product_code, target_code),
    CONSTRAINT fk_product_targets_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_product_targets_target
        FOREIGN KEY (target_code) REFERENCES gift_targets(target_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_product_targets_target (target_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_age_groups (
    product_code VARCHAR(20) NOT NULL,
    age_group_code VARCHAR(20) NOT NULL,
    note TEXT,
    PRIMARY KEY (product_code, age_group_code),
    CONSTRAINT fk_product_age_groups_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_product_age_groups_age
        FOREIGN KEY (age_group_code) REFERENCES age_groups(age_group_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_product_age_groups_age (age_group_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_keywords (
    product_code VARCHAR(20) NOT NULL,
    keyword_code VARCHAR(20) NOT NULL,
    note TEXT,
    PRIMARY KEY (product_code, keyword_code),
    CONSTRAINT fk_product_keywords_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_product_keywords_keyword
        FOREIGN KEY (keyword_code) REFERENCES keywords(keyword_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_product_keywords_keyword (keyword_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_links (
    link_code VARCHAR(20) PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL,
    link_type VARCHAR(50),
    site_name VARCHAR(100),
    url TEXT NOT NULL,
    is_primary TINYINT(1) NOT NULL DEFAULT 0,
    note TEXT,
    CONSTRAINT fk_product_links_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_product_links_product (product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product_purchase_locations (
    product_code VARCHAR(20) NOT NULL,
    location_code VARCHAR(20) NOT NULL,
    availability_status VARCHAR(50),
    note TEXT,
    PRIMARY KEY (product_code, location_code),
    CONSTRAINT fk_product_purchase_locations_product
        FOREIGN KEY (product_code) REFERENCES products(product_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_product_purchase_locations_location
        FOREIGN KEY (location_code) REFERENCES purchase_locations(location_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_product_purchase_locations_location (location_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
