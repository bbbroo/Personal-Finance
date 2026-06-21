"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-21
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _create(sql: str) -> None:
    op.execute(sql)


def upgrade() -> None:
    _create(
        """
        CREATE TABLE accounts (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(200) NOT NULL,
            institution VARCHAR(200),
            account_type VARCHAR(50) NOT NULL,
            account_subtype VARCHAR(100),
            valuation_method VARCHAR(50) NOT NULL,
            balance_sign_policy VARCHAR(50) NOT NULL,
            currency VARCHAR(3) NOT NULL,
            is_active BOOLEAN NOT NULL,
            include_in_net_worth BOOLEAN NOT NULL,
            include_in_budget BOOLEAN NOT NULL,
            include_in_cash_flow BOOLEAN NOT NULL,
            data_source VARCHAR(50) NOT NULL,
            freshness_threshold_days INTEGER NOT NULL,
            notes TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE app_settings (
            "key" VARCHAR(100) NOT NULL,
            value_json JSON NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY ("key")
        )
        """
    )
    _create(
        """
        CREATE TABLE audit_log (
            id VARCHAR(36) NOT NULL,
            entity_type VARCHAR(80) NOT NULL,
            entity_id VARCHAR(100) NOT NULL,
            action VARCHAR(80) NOT NULL,
            before_json JSON,
            after_json JSON,
            source VARCHAR(50) NOT NULL,
            source_id VARCHAR(100),
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE backup_manifests (
            id VARCHAR(36) NOT NULL,
            backup_type VARCHAR(50) NOT NULL,
            backup_path TEXT NOT NULL,
            manifest_path TEXT NOT NULL,
            app_version VARCHAR(50) NOT NULL,
            schema_version VARCHAR(100) NOT NULL,
            database_sha256 VARCHAR(64) NOT NULL,
            created_at DATETIME NOT NULL,
            notes TEXT,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE budget_periods (
            id VARCHAR(36) NOT NULL,
            period_type VARCHAR(50) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL,
            closed_at DATETIME,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE category_groups (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(150) NOT NULL,
            group_type VARCHAR(50) NOT NULL,
            sort_order INTEGER NOT NULL,
            is_system BOOLEAN NOT NULL,
            is_active BOOLEAN NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (name)
        )
        """
    )
    _create(
        """
        CREATE TABLE daily_refresh_runs (
            id VARCHAR(36) NOT NULL,
            run_date DATE NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            status VARCHAR(50) NOT NULL,
            refreshed_prices BOOLEAN NOT NULL,
            refreshed_coinbase BOOLEAN NOT NULL,
            created_snapshot BOOLEAN NOT NULL,
            errors_json JSON,
            warnings_json JSON,
            PRIMARY KEY (id),
            UNIQUE (run_date)
        )
        """
    )
    _create(
        """
        CREATE TABLE data_quality_issues (
            id VARCHAR(36) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            issue_type VARCHAR(80) NOT NULL,
            entity_type VARCHAR(80),
            entity_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            recommended_action TEXT,
            status VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL,
            resolved_at DATETIME,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE goals (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(200) NOT NULL,
            goal_type VARCHAR(80) NOT NULL,
            target_cents INTEGER NOT NULL,
            current_manual_cents INTEGER,
            target_date DATE,
            status VARCHAR(50) NOT NULL,
            progress_method VARCHAR(80) NOT NULL,
            notes TEXT,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE import_mapping_presets (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(150) NOT NULL,
            institution VARCHAR(150),
            import_type VARCHAR(50) NOT NULL,
            version INTEGER NOT NULL,
            mapping_json JSON NOT NULL,
            sign_policy VARCHAR(80) NOT NULL,
            date_format VARCHAR(50),
            amount_format VARCHAR(50),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE instruments (
            id VARCHAR(36) NOT NULL,
            symbol VARCHAR(40) NOT NULL,
            provider_symbol VARCHAR(80),
            name VARCHAR(200) NOT NULL,
            instrument_type VARCHAR(50) NOT NULL,
            exchange VARCHAR(80),
            cusip_or_isin VARCHAR(80),
            default_asset_class VARCHAR(50) NOT NULL,
            price_provider VARCHAR(80),
            is_active BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_instrument_symbol_type UNIQUE (symbol, instrument_type)
        )
        """
    )
    _create(
        """
        CREATE TABLE monthly_review_snapshots (
            id VARCHAR(36) NOT NULL,
            review_month VARCHAR(7) NOT NULL,
            status VARCHAR(50) NOT NULL,
            starting_net_worth_cents INTEGER,
            ending_net_worth_cents INTEGER,
            net_worth_change_cents INTEGER,
            income_cents INTEGER,
            expenses_cents INTEGER,
            savings_rate_decimal VARCHAR(50),
            investment_value_change_cents INTEGER,
            top_spending_categories_json JSON NOT NULL,
            biggest_transactions_json JSON NOT NULL,
            budget_variance_json JSON NOT NULL,
            data_quality_summary_json JSON NOT NULL,
            source_data_hash VARCHAR(64) NOT NULL,
            finalized_at DATETIME,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (review_month)
        )
        """
    )
    _create(
        """
        CREATE TABLE transfer_links (
            id VARCHAR(36) NOT NULL,
            confidence_score VARCHAR(20) NOT NULL,
            match_basis VARCHAR(200) NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_by VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL,
            confirmed_at DATETIME,
            PRIMARY KEY (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE account_balance_snapshots (
            id VARCHAR(36) NOT NULL,
            account_id VARCHAR(36) NOT NULL,
            snapshot_date DATE NOT NULL,
            balance_cents INTEGER,
            balance_kind VARCHAR(50) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            source_id VARCHAR(100),
            confidence VARCHAR(20) NOT NULL,
            is_reconciled BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_balance_lineage UNIQUE (account_id, snapshot_date, balance_kind, source_id),
            FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE CASCADE
        )
        """
    )
    _create(
        """
        CREATE TABLE categories (
            id VARCHAR(36) NOT NULL,
            group_id VARCHAR(36) NOT NULL,
            name VARCHAR(150) NOT NULL,
            category_type VARCHAR(50) NOT NULL,
            budget_behavior VARCHAR(50) NOT NULL,
            is_system BOOLEAN NOT NULL,
            is_active BOOLEAN NOT NULL,
            sort_order INTEGER NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(group_id) REFERENCES category_groups (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE holding_snapshots (
            id VARCHAR(36) NOT NULL,
            account_id VARCHAR(36) NOT NULL,
            instrument_id VARCHAR(36) NOT NULL,
            snapshot_date DATE NOT NULL,
            valuation_timestamp DATETIME,
            quantity_decimal VARCHAR(80) NOT NULL,
            price_decimal VARCHAR(80),
            market_value_cents INTEGER,
            cost_basis_cents INTEGER,
            unrealized_gain_loss_cents INTEGER,
            unrealized_gain_loss_pct VARCHAR(80),
            cost_basis_source VARCHAR(80) NOT NULL,
            cost_basis_quality VARCHAR(80) NOT NULL,
            market_value_source VARCHAR(80) NOT NULL,
            valuation_quality VARCHAR(80) NOT NULL,
            confidence VARCHAR(20) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            source_id VARCHAR(100),
            is_current BOOLEAN NOT NULL,
            replaces_snapshot_id VARCHAR(36),
            notes TEXT,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_holding_lineage UNIQUE (account_id, instrument_id, snapshot_date, source_id),
            FOREIGN KEY(account_id) REFERENCES accounts (id),
            FOREIGN KEY(instrument_id) REFERENCES instruments (id),
            FOREIGN KEY(replaces_snapshot_id) REFERENCES holding_snapshots (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE import_batches (
            id VARCHAR(36) NOT NULL,
            import_type VARCHAR(50) NOT NULL,
            institution VARCHAR(150),
            account_id VARCHAR(36),
            original_filename VARCHAR(255) NOT NULL,
            original_file_path TEXT NOT NULL,
            original_file_sha256 VARCHAR(64) NOT NULL,
            normalized_file_path TEXT,
            mapping_preset_id VARCHAR(36),
            mapping_preset_version INTEGER,
            parser_version VARCHAR(80) NOT NULL,
            status VARCHAR(50) NOT NULL,
            row_count INTEGER NOT NULL,
            valid_row_count INTEGER NOT NULL,
            skipped_row_count INTEGER NOT NULL,
            duplicate_row_count INTEGER NOT NULL,
            warning_count INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            committed_record_manifest_json JSON,
            committed_at DATETIME,
            rolled_back_at DATETIME,
            created_at DATETIME NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(account_id) REFERENCES accounts (id),
            FOREIGN KEY(mapping_preset_id) REFERENCES import_mapping_presets (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE liabilities (
            id VARCHAR(36) NOT NULL,
            account_id VARCHAR(36) NOT NULL,
            liability_type VARCHAR(80) NOT NULL,
            current_balance_cents INTEGER NOT NULL,
            credit_limit_cents INTEGER,
            minimum_payment_cents INTEGER,
            due_day INTEGER,
            status VARCHAR(50) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            confidence VARCHAR(20) NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(account_id) REFERENCES accounts (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE prices (
            id VARCHAR(36) NOT NULL,
            instrument_id VARCHAR(36) NOT NULL,
            price_date DATE NOT NULL,
            price_decimal VARCHAR(80) NOT NULL,
            currency VARCHAR(3) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            provider VARCHAR(100),
            provider_symbol VARCHAR(80),
            market_session VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            confidence VARCHAR(20) NOT NULL,
            fetched_at DATETIME,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_price_lineage UNIQUE (instrument_id, price_date, provider),
            FOREIGN KEY(instrument_id) REFERENCES instruments (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE symbol_allocation_overrides (
            id VARCHAR(36) NOT NULL,
            instrument_id VARCHAR(36) NOT NULL,
            asset_class VARCHAR(50) NOT NULL,
            allocation_percent VARCHAR(30) NOT NULL,
            effective_date DATE,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(instrument_id) REFERENCES instruments (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE account_statements (
            id VARCHAR(36) NOT NULL,
            account_id VARCHAR(36) NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            opening_balance_cents INTEGER,
            ending_balance_cents INTEGER,
            source VARCHAR(50) NOT NULL,
            import_batch_id VARCHAR(36),
            status VARCHAR(50) NOT NULL,
            created_at DATETIME NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(account_id) REFERENCES accounts (id),
            FOREIGN KEY(import_batch_id) REFERENCES import_batches (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE budget_category_plans (
            id VARCHAR(36) NOT NULL,
            budget_period_id VARCHAR(36) NOT NULL,
            category_id VARCHAR(36) NOT NULL,
            planned_cents INTEGER NOT NULL,
            rollover_enabled BOOLEAN NOT NULL,
            plan_type VARCHAR(50) NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(budget_period_id) REFERENCES budget_periods (id),
            FOREIGN KEY(category_id) REFERENCES categories (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE goal_account_links (
            id VARCHAR(36) NOT NULL,
            goal_id VARCHAR(36) NOT NULL,
            account_id VARCHAR(36),
            liability_id VARCHAR(36),
            allocation_percent VARCHAR(30),
            PRIMARY KEY (id),
            FOREIGN KEY(goal_id) REFERENCES goals (id) ON DELETE CASCADE,
            FOREIGN KEY(account_id) REFERENCES accounts (id),
            FOREIGN KEY(liability_id) REFERENCES liabilities (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE liability_terms_history (
            id VARCHAR(36) NOT NULL,
            liability_id VARCHAR(36) NOT NULL,
            effective_date DATE NOT NULL,
            apr_decimal VARCHAR(30),
            minimum_payment_cents INTEGER,
            promo_apr_decimal VARCHAR(30),
            promo_end_date DATE,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(liability_id) REFERENCES liabilities (id) ON DELETE CASCADE
        )
        """
    )
    _create(
        """
        CREATE TABLE recurring_transactions (
            id VARCHAR(36) NOT NULL,
            merchant_name VARCHAR(200) NOT NULL,
            account_id VARCHAR(36),
            category_id VARCHAR(36),
            expected_amount_cents INTEGER,
            amount_variability VARCHAR(50) NOT NULL,
            cadence VARCHAR(50) NOT NULL,
            next_expected_date DATE,
            last_seen_date DATE,
            confidence VARCHAR(20) NOT NULL,
            detection_source VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(account_id) REFERENCES accounts (id),
            FOREIGN KEY(category_id) REFERENCES categories (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE rollover_ledger (
            id VARCHAR(36) NOT NULL,
            category_id VARCHAR(36) NOT NULL,
            budget_period_id VARCHAR(36) NOT NULL,
            starting_rollover_cents INTEGER NOT NULL,
            budgeted_cents INTEGER NOT NULL,
            actual_cents INTEGER NOT NULL,
            adjustment_cents INTEGER NOT NULL,
            ending_rollover_cents INTEGER NOT NULL,
            locked_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(category_id) REFERENCES categories (id),
            FOREIGN KEY(budget_period_id) REFERENCES budget_periods (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE sinking_funds (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(150) NOT NULL,
            linked_category_id VARCHAR(36),
            linked_account_id VARCHAR(36),
            target_cents INTEGER NOT NULL,
            due_date DATE,
            monthly_set_aside_cents INTEGER NOT NULL,
            current_balance_cents INTEGER,
            status VARCHAR(50) NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(linked_category_id) REFERENCES categories (id),
            FOREIGN KEY(linked_account_id) REFERENCES accounts (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE staged_import_rows (
            id VARCHAR(36) NOT NULL,
            import_batch_id VARCHAR(36) NOT NULL,
            row_number INTEGER NOT NULL,
            raw_json JSON NOT NULL,
            normalized_json JSON NOT NULL,
            normalized_hash VARCHAR(64) NOT NULL,
            validation_status VARCHAR(50) NOT NULL,
            duplicate_status VARCHAR(50) NOT NULL,
            transfer_status VARCHAR(50) NOT NULL,
            user_action VARCHAR(50) NOT NULL,
            final_record_type VARCHAR(50),
            final_record_id VARCHAR(36),
            errors_json JSON,
            warnings_json JSON,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_staged_row_hash UNIQUE (import_batch_id, normalized_hash),
            FOREIGN KEY(import_batch_id) REFERENCES import_batches (id) ON DELETE CASCADE
        )
        """
    )
    _create(
        """
        CREATE TABLE transaction_rules (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(150) NOT NULL,
            priority INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL,
            match_merchant_contains VARCHAR(200),
            match_description_contains VARCHAR(200),
            match_account_id VARCHAR(36),
            match_amount_min_cents INTEGER,
            match_amount_max_cents INTEGER,
            match_transaction_type VARCHAR(50),
            action_category_id VARCHAR(36),
            action_merchant_name VARCHAR(200),
            action_tags_json JSON,
            stop_processing BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(match_account_id) REFERENCES accounts (id),
            FOREIGN KEY(action_category_id) REFERENCES categories (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE transactions (
            id VARCHAR(36) NOT NULL,
            account_id VARCHAR(36) NOT NULL,
            transaction_date DATE NOT NULL,
            posted_date DATE,
            original_description TEXT NOT NULL,
            merchant_name VARCHAR(255),
            amount_cents INTEGER NOT NULL,
            category_id VARCHAR(36),
            transaction_type VARCHAR(50) NOT NULL,
            transfer_status VARCHAR(50) NOT NULL,
            transfer_link_id VARCHAR(36),
            review_status VARCHAR(50) NOT NULL,
            duplicate_status VARCHAR(50) NOT NULL,
            is_hidden BOOLEAN NOT NULL,
            is_split BOOLEAN NOT NULL,
            fingerprint VARCHAR(64) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            source_id VARCHAR(100),
            created_by_import_batch_id VARCHAR(36),
            updated_by_import_batch_id VARCHAR(36),
            notes TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_transaction_fingerprint UNIQUE (account_id, fingerprint),
            FOREIGN KEY(account_id) REFERENCES accounts (id),
            FOREIGN KEY(category_id) REFERENCES categories (id),
            FOREIGN KEY(transfer_link_id) REFERENCES transfer_links (id),
            FOREIGN KEY(created_by_import_batch_id) REFERENCES import_batches (id),
            FOREIGN KEY(updated_by_import_batch_id) REFERENCES import_batches (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE debt_payment_allocations (
            id VARCHAR(36) NOT NULL,
            transaction_id VARCHAR(36) NOT NULL,
            liability_id VARCHAR(36) NOT NULL,
            principal_cents INTEGER,
            interest_cents INTEGER,
            fee_cents INTEGER,
            is_estimated BOOLEAN NOT NULL,
            confidence VARCHAR(20) NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(transaction_id) REFERENCES transactions (id),
            FOREIGN KEY(liability_id) REFERENCES liabilities (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE reconciliation_runs (
            id VARCHAR(36) NOT NULL,
            account_statement_id VARCHAR(36) NOT NULL,
            calculated_ending_balance_cents INTEGER,
            difference_cents INTEGER,
            status VARCHAR(50) NOT NULL,
            tolerance_cents INTEGER NOT NULL,
            run_at DATETIME NOT NULL,
            notes TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(account_statement_id) REFERENCES account_statements (id)
        )
        """
    )
    _create(
        """
        CREATE TABLE transaction_splits (
            id VARCHAR(36) NOT NULL,
            transaction_id VARCHAR(36) NOT NULL,
            category_id VARCHAR(36) NOT NULL,
            amount_cents INTEGER NOT NULL,
            notes TEXT,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES categories (id)
        )
        """
    )


def downgrade() -> None:
    for table_name in [
        "transaction_splits",
        "reconciliation_runs",
        "debt_payment_allocations",
        "transactions",
        "transaction_rules",
        "staged_import_rows",
        "sinking_funds",
        "rollover_ledger",
        "recurring_transactions",
        "liability_terms_history",
        "goal_account_links",
        "budget_category_plans",
        "account_statements",
        "symbol_allocation_overrides",
        "prices",
        "liabilities",
        "import_batches",
        "holding_snapshots",
        "categories",
        "account_balance_snapshots",
        "transfer_links",
        "monthly_review_snapshots",
        "instruments",
        "import_mapping_presets",
        "goals",
        "data_quality_issues",
        "daily_refresh_runs",
        "category_groups",
        "budget_periods",
        "backup_manifests",
        "audit_log",
        "app_settings",
        "accounts",
    ]:
        op.drop_table(table_name)
