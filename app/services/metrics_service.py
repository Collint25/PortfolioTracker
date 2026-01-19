"""Metrics aggregation service for analytics dashboard."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.calculations import gain_loss, pl_over_time
from app.models import Position, TradeLot
from app.services import lot_service


@dataclass
class MetricsSummary:
    """Summary statistics for portfolio performance."""

    total_realized_pl: Decimal
    total_unrealized_pl: Decimal
    win_rate: float  # 0.0 to 1.0
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass
class PLDataPoint:
    """Single data point for P/L time series."""

    date: date
    cumulative_pl: Decimal


@dataclass
class MetricsFilter:
    """Filter parameters applied to metrics query."""

    account_ids: list[int] | None
    start_date: date | None
    end_date: date | None


@dataclass
class MetricsResult:
    """Complete metrics response with summary and time series."""

    summary: MetricsSummary
    pl_over_time: list[PLDataPoint]
    filters_applied: MetricsFilter


def get_metrics(
    db: Session,
    account_ids: list[int] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> MetricsResult:
    """
    Get portfolio metrics with optional filtering.

    Args:
        db: Database session
        account_ids: Filter to specific accounts (None = all)
        start_date: Include lots closed on/after this date
        end_date: Include lots closed on/before this date

    Returns:
        MetricsResult with summary stats and P/L time series
    """
    # Get P/L summary from lot_service (already has date filtering)
    pl_summary = lot_service.get_pl_summary(
        db,
        account_ids=account_ids,
        start_date=start_date,
        end_date=end_date,
    )

    # Get lots for time series
    query = db.query(TradeLot).filter(TradeLot.is_closed == True)  # noqa: E712
    if account_ids:
        query = query.filter(TradeLot.account_id.in_(account_ids))
    # Note: date filtering for time series would need same subquery logic
    # For MVP, we show all closed lots in time series
    lots = query.all()
    time_series = pl_over_time(lots)

    # Calculate unrealized P/L from positions
    position_query = db.query(Position)
    if account_ids:
        position_query = position_query.filter(Position.account_id.in_(account_ids))
    positions = position_query.all()

    total_unrealized = Decimal("0")
    for pos in positions:
        gl = gain_loss(pos)
        if gl is not None:
            total_unrealized += gl

    # Build result
    summary = MetricsSummary(
        total_realized_pl=pl_summary["total_pl"],
        total_unrealized_pl=total_unrealized,
        win_rate=pl_summary["win_rate"] / 100,  # Convert to 0-1 range
        total_trades=pl_summary["closed_count"],
        winning_trades=pl_summary["winners"],
        losing_trades=pl_summary["losers"],
    )

    pl_data_points = [
        PLDataPoint(date=dp["date"], cumulative_pl=dp["cumulative_pl"])
        for dp in time_series
    ]

    filters = MetricsFilter(
        account_ids=account_ids,
        start_date=start_date,
        end_date=end_date,
    )

    return MetricsResult(
        summary=summary,
        pl_over_time=pl_data_points,
        filters_applied=filters,
    )
