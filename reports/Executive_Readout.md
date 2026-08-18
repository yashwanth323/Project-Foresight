# Zidio Project FORESIGHT Executive Readout
This document outlines the structured slide deck content (10 slides) for the Project FORESIGHT executive review.

---

## Slide 1: Title Slide & Business Problem
* **Slide Title**: Project FORESIGHT: AI-Powered Demand Forecasting & Inventory Intelligence
* **Subtitle**: Optimizing Working Capital and Supply Chain Resilience
* **Key Content**:
  * Demand planning in traditional supermarkets suffers from high forecast errors, leading to severe stockouts on key items (milk, bread) and excessive capital locked in slow-moving items (shampoo).
  * Existing daily workflows are highly volatile and reactive.
  * **Objective**: Deploy weekly SKU-level forecasting and a localized Decision Reorder Engine to minimize stockout revenue leakage and free up locked working capital.

---

## Slide 2: The FORESIGHT Solution
* **Slide Title**: Transitioning from Reactive to Predictive Planning
* **Key Content**:
  * **Weekly Aggregation**: Daily sales consolidated into standard weekly segments starting Mondays, smoothing out daily noise.
  * **Out-of-Sample Evaluation**: Models compete dynamically on out-of-sample holdout folds using the WAPE metric.
  * **Replenishment Action Grid**: Every SKU is automatically mapped to a distinct action: `REORDER NOW`, `MARKDOWN / CLEAR`, `WATCH / VOLATILE`, or `HEALTHY`.
  * **Modern SaaS Interface**: Glassmorphism premium dashboard for operations managers and planners.

---

## Slide 3: Data Architecture & Methodology
* **Slide Title**: Structured Ingestion and Leak-Free Engineering
* **Key Content**:
  * **Four Clean Tables**: Ingests daily transaction fact tables (`sales_daily`), catalog metadata (`sku_master`), event calendars (`calendar`), and periodic levels (`inventory_snapshots`).
  * **PD.merge_asof Join**: Safely forward-fills periodic inventory snapshots to sales records, preventing lookahead bias.
  * **Leakage-Free Features**: Engineers lag variables (1, 7, 14, 28 weeks) and rolling statistics (mean and standard deviation over 7, 14, 28 weeks) shifted by 1 week to strictly prevent temporal leakage.

---

## Slide 4: Forecast Engine & Out-of-Sample Backtesting
* **Slide Title**: Dynamic Selection: Seasonal-Naive vs. Random Forest
* **Key Content**:
  * **Rolling-Origin Backtesting**: 4 chronological validation folds simulating real-world weekly planning cycles.
  * **Primary Metric**: Weighted Absolute Percentage Error (WAPE):
    $$\text{WAPE} = \frac{\sum |Y_t - \hat{Y}_t|}{\sum |Y_t|}$$
  * **Normalized Bias**: Track direction of error (over-forecasting vs. under-forecasting).
  * **Honest Model Selection**: The engine evaluates both models out-of-sample and automatically saves the champion model to `model.pkl`.

---

## Slide 5: Stockout and Overstock Risk Assessment
* **Slide Title**: Explainable Risk Rules and Operational Triggers
* **Key Content**:
  * **Lead Time Demand**: Average daily demand multiplied by SKU-specific lead time (days).
  * **Stockout Risk Trigger**: Current stock + On-order stock < Lead Time Demand (triggering a `REORDER NOW` decision).
  * **Reorder Point (ROP)**:
    $$\text{ROP} = \text{Daily Demand} \times (\text{Lead Time Days} + \text{Safety Stock Days})$$
  * **Overstock Risk Trigger**: Current stock on hand > 1.5x expected demand over a 6-week forward window (triggering a `MARKDOWN / CLEAR` decision).

---

## Slide 6: Financial Business Impact in Rupees (₹)
* **Slide Title**: Translating Quantities to Financial Outcomes
* **Key Content**:
  * **Sales at Risk (₹)**: Represents potential lost revenue from near-term stockouts.
    $$\text{Sales at Risk} = \text{Shortage Units} \times \text{List Price}$$
  * **Capital Locked (₹)**: Represents idle cash trapped in excessive, slow-moving stock.
    $$\text{Capital Locked} = \text{Excess Units} \times \text{Unit Cost}$$
  * **Business Outcome**: Planners can instantly sort and prioritize SKU interventions by Rupee impact, targeting high-value items first.

---

## Slide 7: Prioritized Recommended Actions
* **Slide Title**: Operational Action Plan & Priority Mapping
* **Key Content**:
  * **REORDER NOW**: Reorder suggested quantity `(ROP - Available Stock)` immediately. (Priority: Critical/High).
  * **MARKDOWN / CLEAR**: Halt procurement; run promotional discounts (10% - 25% off list price) to increase volume velocity and recover liquidity. (Priority: Medium/Low).
  * **WATCH / VOLATILE**: Maintain safety buffers due to high demand standard deviation or recent promo spikes.
  * **HEALTHY**: No action required; inventory matches demand expectation.

---

## Slide 8: The Dashboard & Product Interface
* **Slide Title**: Real-Time Planning Control Center
* **Key Content**:
  * **Dashboard view**: High-level financial KPIs, sales timelines, action distributions, and prioritized tables.
  * **Forecast view**: Actuals vs. baseline vs. forecast charts with detailed projections.
  * **SKU Explorer**: Single SKU deep-dive with margins, coverage days, and timeline plots.
  * **Reports & Exports**: Full downloadable registries in CSV and Excel formats.
  * **Scoring REST API**: Deployed endpoints `/predict` and `/risk` for corporate supply chain integrations.

---

## Slide 9: Project Limitations
* **Slide Title**: Constraints & Improvement Vectors
* **Key Content**:
  * **Data History Span**: A minimum of 52 weeks is required to capture yearly seasonal patterns (such as Diwali/New Year demand spikes). Current 180-day feeds limit seasonality to a 4-week cycle.
  * **Lead Time Assumptions**: Assumes historical lead times remain constant; does not account for supplier capacity limits or logistics disruptions.
  * **New Product Launch**: Lacks cold-start modeling for SKUs with less than 4 weeks of sales.

---

## Slide 10: Conclusion
* **Slide Title**: Empowering Data-Driven Retail
* **Key Content**:
  * FORESIGHT successfully aggregates daily noise, evaluates models chronologically, and converts raw data into actionable retail orders.
  * **Next Steps**:
    1. Connect API server to the main inventory ERP system.
    2. Expand the dataset to 2 years of daily data to train deep LSTM or XGBoost models.
    3. Run a A/B test in a single supermarket branch to measure working capital reduction.
