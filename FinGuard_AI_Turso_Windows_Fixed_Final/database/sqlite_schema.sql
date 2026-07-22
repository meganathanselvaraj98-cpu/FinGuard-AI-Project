-- FinGuard AI SQLite-compatible schema reference
-- The application creates this schema automatically on first run.
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;

CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	entity_type VARCHAR(80), 
	entity_id VARCHAR(80), 
	ip_address VARCHAR(64), 
	user_agent VARCHAR(255), 
	details_json TEXT, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE bank_accounts (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	nickname VARCHAR(80) NOT NULL, 
	bank_name_encrypted TEXT NOT NULL, 
	holder_name_encrypted TEXT NOT NULL, 
	account_number_encrypted TEXT NOT NULL, 
	account_number_hash VARCHAR(64) NOT NULL, 
	account_last4 VARCHAR(4) NOT NULL, 
	ifsc_encrypted TEXT NOT NULL, 
	account_type_encrypted TEXT, 
	branch_encrypted TEXT, 
	is_primary BOOLEAN NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_account_hash UNIQUE (user_id, account_number_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE budgets (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	category_name VARCHAR(100) NOT NULL, 
	budget_month DATE NOT NULL, 
	allocated_amount NUMERIC(15, 2) NOT NULL, 
	alert_threshold_percent FLOAT NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_budget_month_category UNIQUE (user_id, category_name, budget_month), 
	CONSTRAINT ck_budget_amount_positive CHECK (allocated_amount > 0), 
	CONSTRAINT ck_budget_threshold CHECK (alert_threshold_percent >= 1 AND alert_threshold_percent <= 100), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE categories (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	category_type VARCHAR(8) NOT NULL, 
	icon VARCHAR(20) NOT NULL, 
	is_system BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_category_type UNIQUE (name, category_type)
);

CREATE TABLE predictions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	prediction_type VARCHAR(60) NOT NULL, 
	predicted_value FLOAT, 
	predicted_label VARCHAR(100), 
	model_name VARCHAR(120) NOT NULL, 
	metrics_json TEXT, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE reports (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	report_type VARCHAR(80) NOT NULL, 
	report_format VARCHAR(20) NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	file_path VARCHAR(500) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE statement_imports (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	bank_account_id INTEGER, 
	label VARCHAR(160) NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	file_type VARCHAR(20) NOT NULL, 
	statement_hash VARCHAR(64) NOT NULL, 
	period_start DATE, 
	period_end DATE, 
	raw_rows INTEGER NOT NULL, 
	imported_rows INTEGER NOT NULL, 
	duplicate_rows INTEGER NOT NULL, 
	error_rows INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(bank_account_id) REFERENCES bank_accounts (id) ON DELETE SET NULL
);

CREATE TABLE transactions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	bank_account_id INTEGER, 
	statement_import_id INTEGER, 
	category_id INTEGER, 
	transaction_id_encrypted TEXT, 
	transaction_id_hash VARCHAR(64), 
	transaction_date DATETIME NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	transaction_type VARCHAR(8) NOT NULL, 
	amount NUMERIC(15, 2) NOT NULL, 
	balance_after NUMERIC(15, 2), 
	currency_code VARCHAR(3) NOT NULL, 
	payment_mode VARCHAR(60), 
	merchant VARCHAR(160), 
	is_recurring BOOLEAN NOT NULL, 
	is_unusual BOOLEAN NOT NULL, 
	risk_level VARCHAR(20) NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	source_file_name VARCHAR(255), 
	fingerprint VARCHAR(64) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_transaction_fingerprint UNIQUE (user_id, fingerprint), 
	CONSTRAINT ck_transaction_amount_positive CHECK (amount > 0), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(bank_account_id) REFERENCES bank_accounts (id) ON DELETE SET NULL, 
	FOREIGN KEY(statement_import_id) REFERENCES statement_imports (id) ON DELETE SET NULL, 
	FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE TABLE user_preferences (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	preferred_currency VARCHAR(3) NOT NULL, 
	default_dashboard_scope VARCHAR(40) NOT NULL, 
	risk_preference VARCHAR(20) NOT NULL, 
	investment_horizon VARCHAR(30) NOT NULL, 
	monthly_investment_target NUMERIC(15, 2) NOT NULL, 
	alerts_enabled BOOLEAN NOT NULL, 
	compact_tables BOOLEAN NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE user_profiles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	phone_encrypted TEXT, 
	dob_encrypted TEXT, 
	gender_encrypted TEXT, 
	address_encrypted TEXT, 
	city_encrypted TEXT, 
	occupation_encrypted TEXT, 
	monthly_income_encrypted TEXT, 
	pan_encrypted TEXT, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE users (
	id INTEGER NOT NULL, 
	public_id VARCHAR(36) NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(190) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(5) NOT NULL, 
	status VARCHAR(8) NOT NULL, 
	failed_login_attempts INTEGER NOT NULL, 
	locked_until DATETIME, 
	last_login_at DATETIME, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (public_id)
);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE INDEX ix_bank_accounts_account_number_hash ON bank_accounts (account_number_hash);

CREATE INDEX ix_bank_accounts_user_id ON bank_accounts (user_id);

CREATE INDEX ix_budgets_user_id ON budgets (user_id);

CREATE INDEX ix_predictions_user_id ON predictions (user_id);

CREATE INDEX ix_reports_user_id ON reports (user_id);

CREATE INDEX ix_statement_imports_bank_account_id ON statement_imports (bank_account_id);

CREATE INDEX ix_statement_imports_created_at ON statement_imports (created_at);

CREATE INDEX ix_statement_imports_statement_hash ON statement_imports (statement_hash);

CREATE INDEX ix_statement_imports_user_id ON statement_imports (user_id);

CREATE INDEX ix_transactions_bank_account_id ON transactions (bank_account_id);

CREATE INDEX ix_transactions_fingerprint ON transactions (fingerprint);

CREATE INDEX ix_transactions_statement_import_id ON transactions (statement_import_id);

CREATE INDEX ix_transactions_transaction_date ON transactions (transaction_date);

CREATE INDEX ix_transactions_transaction_id_hash ON transactions (transaction_id_hash);

CREATE INDEX ix_transactions_transaction_type ON transactions (transaction_type);

CREATE INDEX ix_transactions_user_id ON transactions (user_id);

CREATE UNIQUE INDEX ix_user_preferences_user_id ON user_preferences (user_id);

CREATE UNIQUE INDEX ix_users_email ON users (email);

-- Default category seed data (safe to rerun)
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Food & Dining', 'EXPENSE', '🍽️', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Groceries', 'EXPENSE', '🛒', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Transport', 'EXPENSE', '🚕', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Housing', 'EXPENSE', '🏠', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Rent', 'EXPENSE', '🏡', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Utilities', 'EXPENSE', '💡', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Healthcare', 'EXPENSE', '🏥', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Education', 'EXPENSE', '🎓', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Entertainment', 'EXPENSE', '🎬', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Shopping', 'EXPENSE', '🛍️', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Subscriptions', 'EXPENSE', '🔁', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('EMI & Debt', 'EXPENSE', '💳', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Insurance', 'EXPENSE', '🛡️', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Investment', 'EXPENSE', '📈', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Household', 'EXPENSE', '🧹', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Other Expense', 'EXPENSE', '📌', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Salary', 'INCOME', '💼', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Freelance', 'INCOME', '🧑‍💻', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Business', 'INCOME', '🏢', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Interest', 'INCOME', '🏦', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Refund', 'INCOME', '↩️', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Investment Return', 'INCOME', '📊', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Other Income', 'INCOME', '💰', 1, 1);
INSERT OR IGNORE INTO categories (name, category_type, icon, is_system, is_active) VALUES ('Internal Transfer', 'TRANSFER', '🔄', 1, 1);
