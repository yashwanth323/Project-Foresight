# Project FORESIGHT Requirements Checklist & Verification Status

This document tracks each official Zidio FORESIGHT requirement and verifies its implementation status.

| ID | Zidio Acceptance Criteria | Implementation Status | Verified In / File Path |
|:---|:---|:---:|:---|
| **D1** | Ingest 4 daily tables: sales, sku catalog, calendar, inventory snaps | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D1** | Validate schemas, data types, and required fields | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D1** | Clean columns, dates, drop duplicates, handle missing values | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D2** | Aggregate daily records to weekly Monday starts | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D2** | Join calendar and periodic inventory snapshots (forward fill) | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D3** | Engineer lag variables (1, 7, 14, 28 weeks) group-by SKU | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D3** | Engineer rolling stats (mean, std over 7, 14, 28 weeks) group-by SKU | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D3** | Prevents temporal lookahead leakage (shift(1) before rolling) | **PASSED** | [pipeline.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/pipeline.py) |
| **D4** | Build Seasonal-Naive baseline forecast (period = 4 weeks) | **PASSED** | [forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/forecast.py) |
| **D4** | Primary metric WAPE implemented | **PASSED** | [forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/forecast.py) |
| **D4** | Secondary metric Forecast Bias implemented | **PASSED** | [forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/forecast.py) |
| **D4** | Chronological rolling-origin backtesting (folds=4, horizon=4) | **PASSED** | [forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/forecast.py) |
| **D4** | Dynamic model selection (honestly chooses lower backtest WAPE) | **PASSED** | [forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/forecast.py) |
| **D5** | Dashboard filters: category, subcategory, SKU selection, action | **PASSED** | [Dashboard.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/pages/Dashboard.py) |
| **D5** | Actual vs Baseline vs Forecast line plot timeline | **PASSED** | [Forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/pages/Forecast.py) |
| **D5** | Prioritized replenishment lists (Reorder, Markdown/Clear) | **PASSED** | [Dashboard.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/pages/Dashboard.py) |
| **D6** | Centralized inventory risk configuration and triggers | **PASSED** | [risk.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/risk.py) |
| **D6** | Action decision mapping (REORDER NOW, MARKDOWN, WATCH, HEALTHY) | **PASSED** | [risk.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/risk.py) |
| **D6** | Rupee Business Impact (Sales at Risk, Capital Locked in ₹) | **PASSED** | [risk.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/src/risk.py) |
| **D6** | SKU Explorer: single SKU drilldown with margins and stock levels | **PASSED** | [Forecast.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/pages/Forecast.py) |
| **D7** | Deployed REST API scoring endpoints `/predict` and `/risk` | **PASSED** | [app_api.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/app_api.py) |
| **D7** | Complete unit test coverage for forecasting and risk calculations | **PASSED** | [test_logic.py](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/tests/test_logic.py) |
| **D7** | Executive 10-slide review outline document | **PASSED** | [Executive_Readout.md](file:///c:/Users/yash1/OneDrive/Desktop/Project_FORESIGHT/reports/Executive_Readout.md) |
