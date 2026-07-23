# A-Share Local Data Contract

## Storage

Use `/Users/mingyuxu/Desktop/因子挖掘/data_lake/tushare/` with immutable endpoint/month raw
partitions, normalized silver tables, versioned gold research panels, and manifests. Never place
the Tushare token in code, logs, or manifests.

```text
raw/<endpoint>/year=YYYY/month=MM/*.parquet
silver/equity_daily/year=YYYY/month=MM/*.parquet
silver/valuation_daily/year=YYYY/month=MM/*.parquet
silver/moneyflow_daily/year=YYYY/month=MM/*.parquet
silver/financial_pit/year=YYYY/month=MM/*.parquet
silver/security_master.parquet
silver/tradability/year=YYYY/month=MM/*.parquet
silver/industry_membership.parquet
silver/universe_membership/<index_code>/*.parquet
gold/labels/<label_version>/*.parquet
gold/admitted_factor_panels/<library_version>/*.parquet
manifests/*.json
```

## Required point-in-time sources

- trade calendar;
- stock master including listed and delisted securities;
- daily OHLCV and amount;
- daily basic fields including turnover and float/total market value;
- adjustment factor;
- suspension and price-limit state;
- ST/name-change intervals;
- CSI 300 and CSI 500 historical constituents;
- historical industry membership;
- benchmark index prices.

## Registered factor data domains

Bind every campaign to `references/data_domains_v1.json`. Only domains with `status=enabled` may
appear in formulas. `enabled_control_only` fields may define masks, universes, neutralization, or
audit checks but may not be used as alpha inputs.

The current audited formula domain is market price/volume plus turnover/size/liquidity. Extend it
in this order:

1. valuation and dividend fields from `daily_basic`;
2. order-size money flow from `moneyflow`, subject to Tushare permission and coverage;
3. income, balance-sheet, cash-flow, and financial-quality fields through a point-in-time builder;
4. forecasts or analyst-style data only after a separate permission and publication-time audit.

Financial rows must become observable on `ann_date` (or the verified public disclosure time), not
on `end_date`. Resolve repeated announcements with an explicit revision policy, retain the source
announcement identity, and use backward-looking as-of joins. Never backfill a later revision into
earlier dates. Daily valuation and money-flow fields are usable only after their trade-date close.

For each domain, audit schema, uniqueness, coverage by date and universe, stale-value duration,
outliers, permission failures, and point-in-time leakage. Changing an enabled domain or field set
creates a new data-domain-registry version and a new campaign; it does not mutate an open campaign.

## Rules

1. Download by endpoint and month with finite retries and explicit failure records.
2. Treat the latest complete trading day as the end date.
3. Preserve raw responses; rebuild silver and gold outputs rather than mutating raw data.
4. Normalize units and schemas in silver tables.
5. Enforce unique `(trade_date, ts_code)` keys and compare dates with the trade calendar.
6. Construct membership, industry, ST, and listing masks with as-of joins.
7. Exclude observations not tradable at the assumed execution price.
8. Retain delisted stocks to avoid survivorship bias.
9. Version each data snapshot and record row counts, schemas, date ranges, requests, and failures.
10. Persist panels only for admitted factors or frozen benchmark libraries.
11. Record `data_domain_registry_hash` and endpoint/field coverage in every campaign manifest.
12. Never infer that an endpoint is usable merely because the API call succeeds; its silver table
    and point-in-time audit must pass first.

## Canonical local pipeline

Run from the project root with Python bytecode disabled:

```bash
/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/download.py \
  --start-date 20150101 --end-date <latest-complete-trading-day>

/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/build.py \
  --start-date 20150101 --end-date <latest-complete-trading-day>

/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/audit.py
```

The downloader treats empty responses from `daily`, `daily_basic`, `adj_factor`, and
`stk_limit` as retryable failures and verifies coverage from parquet contents, not only request
manifests. Do not use a dataset unless the latest quality report has `status=pass`. Bind formal
factor results to the report's `snapshot_id` and exact label/build manifest paths.
