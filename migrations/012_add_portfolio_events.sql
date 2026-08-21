-- Migration 012: the append-only ledger.
--
-- Positions, capital gains, XIRR and dividend attribution are currently three
-- separate computations reading three shapes of data, which is why they
-- disagree. This table is the single record they are all folded from.
--
-- Two design points worth keeping in mind when querying it:
--
--   * Identity is the ISIN, not the symbol. Tickers get renamed (Zomato ->
--     ETERNAL), differ by exchange (.NS / .BO) and differ again by broker
--     (RELIANCE-EQ). The production database already holds thirteen securities
--     as two rows each for exactly this reason.
--
--   * `account` is load-bearing, not decoration. For dematerialised securities
--     FIFO is applied account-wise (CBDT Circular 768): shares in one demat
--     cannot be construed as sold when another demat is debited. Lots must not
--     be pooled across accounts.
--
-- Rows are append-only. A correction is a new compensating event, never an
-- UPDATE, so a tax figure that has already been filed stays reproducible.
--
-- Purely additive: nothing reads this table yet, so applying it changes no
-- existing behaviour and no existing figure.
--
-- Run with, from the repo root:
--     uv run python run_sql_migration.py 012_add_portfolio_events.sql

CREATE TABLE IF NOT EXISTS portfolio_events (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    portfolio_id    INT NULL,

    isin            VARCHAR(12) NOT NULL,
    symbol          VARCHAR(30) NULL,
    account         VARCHAR(60) NOT NULL DEFAULT '',

    event_type      VARCHAR(20) NOT NULL,
    trade_date      DATETIME NOT NULL,

    quantity        DECIMAL(20, 8) NOT NULL DEFAULT 0,
    price           DECIMAL(20, 8) NOT NULL DEFAULT 0,

    brokerage       DECIMAL(20, 4) NULL DEFAULT 0,
    stt             DECIMAL(20, 4) NULL DEFAULT 0,
    other_charges   DECIMAL(20, 4) NULL DEFAULT 0,

    ratio           DECIMAL(20, 8) NULL,
    amount          DECIMAL(20, 4) NULL,

    source          VARCHAR(60) NOT NULL DEFAULT '',
    source_ref      VARCHAR(64) NOT NULL DEFAULT '',

    notes           VARCHAR(500) NULL,
    created_at      DATETIME NOT NULL,

    CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_events_portfolio FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),

    -- Re-importing the same statement must be a no-op rather than a duplicate.
    CONSTRAINT uix_event_source_ref UNIQUE (user_id, source, source_ref)
);

-- The fold's access pattern: one user's events for one instrument, in one
-- account, in date order.
CREATE INDEX IF NOT EXISTS ix_events_user_isin_account_date
    ON portfolio_events (user_id, isin, account, trade_date);

CREATE INDEX IF NOT EXISTS ix_events_isin ON portfolio_events (isin);
CREATE INDEX IF NOT EXISTS ix_events_trade_date ON portfolio_events (trade_date);
CREATE INDEX IF NOT EXISTS ix_events_event_type ON portfolio_events (event_type);

-- ISIN and demat account on the existing tables, so holdings can be resolved
-- to a real instrument and attributed to the account that holds them. Both
-- nullable: existing rows keep working until they are backfilled from a CAS.
ALTER TABLE assets ADD COLUMN IF NOT EXISTS isin VARCHAR(12) NULL;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS demat_account VARCHAR(60) NULL;

CREATE INDEX IF NOT EXISTS ix_assets_isin ON assets (isin);
