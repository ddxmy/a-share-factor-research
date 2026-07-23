# Tushare point-in-time data lake

This pipeline creates a separate, resumable 2015-to-present A-share data lake without changing
the legacy `local_research/data/` files.

Default storage root:

```text
/Users/mingyuxu/Desktop/因子挖掘/data_lake/tushare/
```

Raw endpoint batches are immutable. Each request writes a parquet batch plus a request manifest;
reruns read those manifests and request only dates that have not succeeded. Silver and gold files
are versioned by coverage date or content hash rather than overwritten.

## 1. Inspect the full plan

```bash
/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/download.py --dry-run
```

## 2. Download

```bash
/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/download.py \
  --start-date 20150101 --end-date YYYYMMDD
```

The default daily endpoints are `daily`, `daily_basic`, `adj_factor`, `stk_limit`, `suspend_d`,
and `stock_st`. Reference data includes the trade calendar, listed/delisted securities, SW2014
and SW2021 L1 codebooks, SW2021 point-in-time membership intervals, name changes, CSI 300/CSI
500 weights, and benchmark index prices.

`index_member_all` defaults to current members only. The downloader therefore paginates both
`is_new=Y` and `is_new=N`, preserves inclusive `in_date`/`out_date` intervals, and refuses to mark
the reference snapshot complete unless both current and historical membership rows are present.
The 2012-2019 `5dr_project` daily `SW2014F` files are used as an external overlap check, not copied
into this data lake or silently mixed with the SW2021 taxonomy.

## 3. Build normalized panels and labels

```bash
/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/build.py
```

After a reference-only refresh, rebuild just the versioned reference tables with:

```bash
/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/build.py --reference-only
```

The primary label is next-market-day open-to-close return. The secondary label is adjusted
close-to-close return. Label rows retain execution tradability flags rather than silently filling
unavailable returns.

## 4. Audit and freeze a snapshot

```bash
/opt/miniconda3/bin/python3 -B local_research/lake_pipeline/audit.py
```

Do not run formal factor evaluation unless the resulting quality report is `pass`. A successful
report contains the immutable `snapshot_id` that must be attached to every formal factor result.
The audit measures industry coverage at each `(trade_date, ts_code)` using an as-of interval join;
an "ever appeared in the industry table" match is not accepted as point-in-time coverage.
