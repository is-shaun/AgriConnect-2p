-- AgriConnect MySQL schema (MySQL 8.0+, InnoDB, utf8mb4).
-- Generated from the SQLAlchemy models in backend/app/models (do not edit by hand;
-- regenerate or use `flask db upgrade` / `flask init-db`). Reference / manual setup only.

CREATE DATABASE IF NOT EXISTS agriconnect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE agriconnect;

CREATE TABLE contact_messages (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	subject VARCHAR(150) NOT NULL, 
	message TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE crops (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	description TEXT, 
	unit VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_crops_category ON crops (category);

CREATE TABLE locations (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	state VARCHAR(80) NOT NULL, 
	district VARCHAR(80) NOT NULL, 
	market_name VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_location UNIQUE (state, district, market_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_locations_state_district ON locations (state, district);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_users_role CHECK (role IN ('user', 'admin'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE market_prices (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	crop_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	observation_date DATE NOT NULL, 
	min_price NUMERIC(12, 2) NOT NULL, 
	max_price NUMERIC(12, 2) NOT NULL, 
	modal_price NUMERIC(12, 2) NOT NULL, 
	source VARCHAR(255) NOT NULL, 
	is_demo BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_price_observation UNIQUE (crop_id, location_id, observation_date), 
	CONSTRAINT ck_price_positive CHECK (min_price > 0 AND max_price > 0 AND modal_price > 0), 
	CONSTRAINT ck_price_order CHECK (min_price <= modal_price AND modal_price <= max_price), 
	FOREIGN KEY(crop_id) REFERENCES crops (id) ON DELETE RESTRICT, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_prices_crop_loc_date ON market_prices (crop_id, location_id, observation_date);
CREATE INDEX ix_prices_date ON market_prices (observation_date);

CREATE TABLE predictions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER, 
	crop_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	horizon_weeks SMALLINT NOT NULL, 
	base_date DATE NOT NULL, 
	prediction_date DATE NOT NULL, 
	base_price NUMERIC(12, 2) NOT NULL, 
	predicted_price NUMERIC(12, 2) NOT NULL, 
	range_low NUMERIC(12, 2), 
	range_high NUMERIC(12, 2), 
	model_version VARCHAR(80) NOT NULL, 
	is_demo BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_prediction_positive CHECK (predicted_price > 0), 
	CONSTRAINT ck_prediction_horizon CHECK (horizon_weeks BETWEEN 1 AND 52), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(crop_id) REFERENCES crops (id), 
	FOREIGN KEY(location_id) REFERENCES locations (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_predictions_created_at ON predictions (created_at);
CREATE INDEX ix_predictions_user_id ON predictions (user_id);
