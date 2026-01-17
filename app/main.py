from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.logging_config import configure_logging
from app.routers import (
    accounts,
    comments,
    linked_trades,
    pages,
    saved_filters,
    sync,
    tags,
    trade_groups,
    transactions,
)

# Configure logging at startup
configure_logging()

app = FastAPI(title="Portfolio Tracker")

templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(pages.router)
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])
app.include_router(trade_groups.router, prefix="/trade-groups", tags=["trade-groups"])
app.include_router(
    linked_trades.router, prefix="/linked-trades", tags=["linked-trades"]
)
app.include_router(
    saved_filters.router, prefix="/saved-filters", tags=["saved-filters"]
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
