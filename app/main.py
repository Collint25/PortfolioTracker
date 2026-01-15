from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.logging_config import configure_logging
from app.routers import accounts, comments, pages, sync, tags, trade_groups, transactions

# Configure logging at startup
configure_logging()

app = FastAPI(title="Portfolio Tracker")

templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(pages.router)
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(comments.router, prefix="/api/comments", tags=["comments"])
app.include_router(trade_groups.router, prefix="/trade-groups", tags=["trade-groups"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
