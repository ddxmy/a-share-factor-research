"""Report tables, figures, and a self-contained HTML research summary."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd

from .evaluation import ICEvaluation
from .portfolio import PortfolioSimulation


REQUIRED_ARTIFACTS = (
    "summary.json",
    "data_quality.csv",
    "ic_summary.csv",
    "ic_daily.csv",
    "portfolio_summary.csv",
    "nav.csv",
    "figures/cumulative_rank_ic.png",
    "figures/annual_ic.png",
    "figures/top_k_nav.png",
    "report.html",
)


def write_report_bundle(
    output_directory: Path,
    *,
    summary: dict[str, Any],
    data_quality: pd.DataFrame,
    ic_evaluation: ICEvaluation,
    portfolio_simulations: tuple[PortfolioSimulation, ...],
) -> None:
    """Write the complete public artifact contract into a staging directory."""
    output_directory = Path(output_directory)
    figures_directory = output_directory / "figures"
    figures_directory.mkdir(parents=True, exist_ok=False)

    ic_summary = _combined_ic_summary(ic_evaluation)
    portfolio_summary = _combined_portfolio_summary(portfolio_simulations)
    nav = _combined_nav(portfolio_simulations)

    (output_directory / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    data_quality.to_csv(output_directory / "data_quality.csv", index=False)
    ic_summary.to_csv(output_directory / "ic_summary.csv", index=False)
    ic_evaluation.daily.to_csv(output_directory / "ic_daily.csv", index=False)
    portfolio_summary.to_csv(output_directory / "portfolio_summary.csv", index=False)
    nav.to_csv(output_directory / "nav.csv", index=False)

    _plot_cumulative_rank_ic(
        ic_evaluation.daily, figures_directory / "cumulative_rank_ic.png"
    )
    _plot_annual_ic(ic_evaluation.yearly, figures_directory / "annual_ic.png")
    _plot_top_k_nav(nav, figures_directory / "top_k_nav.png")
    _write_html_report(
        output_directory / "report.html",
        summary=summary,
        data_quality=data_quality,
        ic_summary=ic_summary,
        portfolio_summary=portfolio_summary,
    )


def _combined_ic_summary(evaluation: ICEvaluation) -> pd.DataFrame:
    overall = evaluation.summary.assign(sample="overlapping", year=pd.NA)
    non_overlapping = evaluation.non_overlapping_summary.assign(
        sample="non_overlapping", year=pd.NA
    )
    annual = evaluation.yearly.assign(sample="annual")
    return pd.concat([overall, non_overlapping, annual], ignore_index=True, sort=False)


def _combined_portfolio_summary(
    simulations: tuple[PortfolioSimulation, ...],
) -> pd.DataFrame:
    if not simulations:
        return pd.DataFrame()
    return pd.concat([simulation.summary for simulation in simulations], ignore_index=True)


def _combined_nav(simulations: tuple[PortfolioSimulation, ...]) -> pd.DataFrame:
    tables: list[pd.DataFrame] = []
    for simulation in simulations:
        for table_kind, table in (
            ("quintile", simulation.quintiles),
            ("top_k", simulation.top_k),
            ("long_short", simulation.long_short),
        ):
            tables.append(table.assign(table_kind=table_kind))
    if not tables:
        return pd.DataFrame()
    return pd.concat(tables, ignore_index=True, sort=False)


def _plot_cumulative_rank_ic(daily: pd.DataFrame, destination: Path) -> None:
    figure, axis = plt.subplots(figsize=(9, 5))
    plotted = False
    for (eligibility, horizon), group in daily.groupby(
        ["eligibility", "horizon_days"], sort=True
    ):
        ordered = group.sort_values("signal_date")
        values = ordered["rank_ic"].astype(float)
        axis.plot(
            ordered["signal_date"],
            values.fillna(0.0).cumsum(),
            label=f"{eligibility} {int(horizon)}D",
        )
        plotted = True
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set(title="Cumulative Rank IC", xlabel="Signal date", ylabel="Cumulative Rank IC")
    if plotted:
        axis.legend(fontsize="small", ncol=2)
    _save_figure(figure, destination)


def _plot_annual_ic(yearly: pd.DataFrame, destination: Path) -> None:
    figure, axis = plt.subplots(figsize=(9, 5))
    plotted = False
    for (eligibility, horizon), group in yearly.groupby(
        ["eligibility", "horizon_days"], sort=True
    ):
        ordered = group.sort_values("year")
        axis.plot(
            ordered["year"],
            ordered["mean_rank_ic"],
            marker="o",
            label=f"{eligibility} {int(horizon)}D",
        )
        plotted = True
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set(title="Annual Mean Rank IC", xlabel="Year", ylabel="Mean Rank IC")
    if plotted:
        axis.legend(fontsize="small", ncol=2)
    _save_figure(figure, destination)


def _plot_top_k_nav(nav: pd.DataFrame, destination: Path) -> None:
    figure, axis = plt.subplots(figsize=(9, 5))
    plotted = False
    top_k = nav.loc[nav.get("table_kind", pd.Series(dtype=str)).eq("top_k")]
    for horizon, group in top_k.groupby("horizon_days", sort=True):
        ordered = group.sort_values("signal_date")
        dates = pd.to_datetime(ordered["nav_date"], errors="coerce").fillna(
            pd.to_datetime(ordered["signal_date"], errors="coerce")
        )
        axis.plot(dates, ordered["gross_nav"], label=f"{int(horizon)}D gross")
        axis.plot(dates, ordered["net_nav"], linestyle="--", label=f"{int(horizon)}D net")
        plotted = True
    axis.axhline(1.0, color="black", linewidth=0.8)
    axis.set(title="Top-K Gross and Net NAV", xlabel="NAV date", ylabel="NAV")
    if plotted:
        axis.legend(fontsize="small", ncol=2)
    _save_figure(figure, destination)


def _save_figure(figure: plt.Figure, destination: Path) -> None:
    figure.tight_layout()
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def _write_html_report(
    destination: Path,
    *,
    summary: dict[str, Any],
    data_quality: pd.DataFrame,
    ic_summary: pd.DataFrame,
    portfolio_summary: pd.DataFrame,
) -> None:
    factor_id = escape(str(summary["factor_id"]))
    decision = escape(str(summary["decision"]))
    registry = summary["registry"]
    formula = escape(str(registry["formula_definition"]))
    date_range = summary["date_range"]
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{factor_id} single-factor report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 1100px; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.84rem; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.35rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
  <h1>{factor_id} single-factor report</h1>
  <p><strong>Decision:</strong> {decision}</p>
  <p><strong>Formula:</strong> {formula}</p>
  <p><strong>Signal window:</strong> {escape(str(date_range['start']))} to {escape(str(date_range['end']))}</p>
  <h2>Data quality</h2>
  {data_quality.to_html(index=False, border=0)}
  <h2>IC evidence</h2>
  <img src="figures/cumulative_rank_ic.png" alt="Cumulative Rank IC">
  <img src="figures/annual_ic.png" alt="Annual Rank IC">
  {ic_summary.to_html(index=False, border=0)}
  <h2>Matched portfolio evidence</h2>
  <img src="figures/top_k_nav.png" alt="Top-K gross and net NAV">
  {portfolio_summary.to_html(index=False, border=0)}
</body>
</html>
"""
    destination.write_text(html, encoding="utf-8")
