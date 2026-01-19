```mermaid
graph LR
    Web_Interface["Web Interface"]
    Sync_Orchestrator["Sync Orchestrator"]
    Domain_Logic_Engine["Domain Logic Engine"]
    Transaction_Manager["Transaction Manager"]
    Filter_System["Filter System"]
    Calculations["Calculations"]
    Market_Data_Service["Market Data Service"]
    Portfolio_Database["Portfolio Database"]
    External_Providers["External Providers"]
    Web_Interface -- "Triggers synchronization jobs based on user actions." --> Sync_Orchestrator
    Web_Interface -- "Requests filtered transaction history for display." --> Transaction_Manager
    Web_Interface -- "Applies saved filters and manages favorites." --> Filter_System
    Sync_Orchestrator -- "Writes normalized account and transaction data." --> Portfolio_Database
    Domain_Logic_Engine -- "Reads transactions, writes TradeLot associations via FIFO matching." --> Portfolio_Database
    Market_Data_Service -- "Fetches real-time pricing data." --> External_Providers
    Sync_Orchestrator -- "Connects to brokerage APIs for account history." --> External_Providers
    Transaction_Manager -- "Executes read-only queries for UI presentation." --> Portfolio_Database
    Calculations -- "Computes P/L and position metrics." --> Portfolio_Database
    Filter_System -- "Reads/writes SavedFilter configurations." --> Portfolio_Database
```

## Details

The PortfolioTracker application employs a Service-Layer Architecture designed to separate the complexity of external data synchronization from user-facing portfolio management. The system operates on a "Sync-Process-Present" flow: raw financial data is ingested via the Sync Orchestrator, refined into meaningful trade lots by the Domain Logic Engine, and served to the user through a Web Interface powered by FastAPI and HTMX.

This separation ensures that the heavy lifting of API integration and data normalization does not impact the responsiveness of the user interface, while the Portfolio Database acts as the central source of truth for both raw transactions and derived investment insights.

### Web Interface
The user-facing layer handling HTTP requests, rendering Jinja2 templates, and managing HTMX partial updates. It acts as the controller, delegating logic to services.

**Related Files:**
- `app/routers/sync.py`
- `app/routers/transactions.py`
- `app/routers/api.py` - autocomplete endpoints

### Sync Orchestrator
The core write-service responsible for synchronizing local state with external brokerage accounts. It handles API authentication, data fetching, and normalization.

**Related Files:**
- `app/services/sync_service.py`
- `app/services/snaptrade_client.py`

### Domain Logic Engine
Encapsulates business logic for organizing raw trades into meaningful portfolios. The TradeLot system tracks share/contract batches through their open→close lifecycle using FIFO matching. LotTransaction records link individual transactions to lots with quantity allocations.

**Related Files:**
- `app/services/lot_service.py` - FIFO lot matching for stocks/options
- `app/models/trade_lot.py` - TradeLot and LotTransaction models

### Transaction Manager
A read-optimized service providing filtered, sorted, and paginated transaction data to the UI. It abstracts complex database queries.

**Related Files:**
- `app/services/transaction_service.py`

### Filter System
Manages SavedFilter configurations, allowing users to save named filter presets with favorite designation. Favorite filters are auto-applied on page load.

**Related Files:**
- `app/services/saved_filter_service.py` - CRUD for saved filters
- `app/services/filters.py` - TransactionFilter dataclass + filter builders
- `app/models/saved_filter.py`

### Calculations
Pure functions for computing profit/loss and position metrics. Separated from services to enable isolated testing and reuse.

**Related Files:**
- `app/calculations/` - P/L and position calculation functions

### Market Data Service
A specialized service for fetching and caching real-time asset prices and historical market data to value positions.

**Related Files:**
- `app/services/market_data_service.py`

### Portfolio Database
The relational data store (SQLite/SQLAlchemy) holding all application state, from raw account data to trade lot associations.

**Related Files:**
- `app/models/transaction.py`
- `app/models/trade_lot.py` - TradeLot and LotTransaction
- `app/models/saved_filter.py`

### External Providers
Third-party APIs providing financial data and brokerage connections.

**Related Files:**
- `app/services/snaptrade_client.py` - SnapTrade API client
