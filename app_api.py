"""Production scoring service and REST API for Project FORESIGHT.

To run: python app_api.py
Exposes:
- GET /predict?sku=<sku_id>
- GET /risk?sku=<sku_id>
- GET /status
"""
from __future__ import annotations

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import pandas as pd
import joblib

from src.risk import score_inventory_risk
from src.forecast import forecast_next_days

ROOT = Path(__file__).resolve().parent


class ScoringAPIHandler(BaseHTTPRequestHandler):
    """Scoring service request handler for weekly demand forecast & inventory risk."""
    
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to console for clean output
        pass

    def send_json_response(self, status_code: int, data: dict):
        """Helper to send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        """Route GET requests to status, predict, and risk endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # 1. Status Check Endpoint
        if path == "/status":
            model_path = ROOT / "model.pkl"
            model_loaded = model_path.exists()
            data_file = ROOT / "data" / "processed" / "sales_clean_weekly.csv"
            data_present = data_file.exists()
            
            self.send_json_response(200, {
                "status": "healthy",
                "service": "FORESIGHT Demand Planning scoring API",
                "model_loaded": model_loaded,
                "data_pipeline_active": data_present,
                "version": "1.0"
            })
            return

        # Load resources for query endpoints
        model_path = ROOT / "model.pkl"
        data_path = ROOT / "data" / "processed" / "sales_clean_weekly.csv"
        
        if not model_path.exists() or not data_path.exists():
            self.send_json_response(503, {
                "error": "Service Unavailable",
                "message": "Forecast model or weekly clean dataset is not generated. Please run the training pipeline first."
            })
            return
            
        try:
            clean_df = pd.read_csv(data_path)
            clean_df["date"] = pd.to_datetime(clean_df["date"])
        except Exception as e:
            self.send_json_response(500, {
                "error": "Internal Server Error",
                "message": f"Unable to load cleaned weekly dataset: {e}"
            })
            return

        # 2. Predict & Risk Endpoints
        if path in ("/predict", "/risk"):
            sku_list = query_params.get("sku")
            if not sku_list:
                self.send_json_response(400, {
                    "error": "Bad Request",
                    "message": "Missing required query parameter: 'sku'. Example: /predict?sku=MILK-1L"
                })
                return
                
            sku_id = sku_list[0].strip()
            
            # Check SKU existence in dataset
            if sku_id not in clean_df["sku_id"].unique():
                self.send_json_response(404, {
                    "error": "Not Found",
                    "message": f"SKU '{sku_id}' not found in active master catalog."
                })
                return
                
            try:
                # Run forecast for next 4 weeks
                forecasts = forecast_next_days(clean_df, model_path, horizon=4)
                forecasts["date"] = pd.to_datetime(forecasts["date"])
                
                # Filter for queried SKU
                sku_fc = forecasts[forecasts["sku_id"] == sku_id].copy()
                
                # Calculate risks
                risks = score_inventory_risk(forecasts)
                sku_risk = risks[risks["sku_id"] == sku_id].iloc[0]
                
                if path == "/predict":
                    # Format weekly prediction results
                    predictions = []
                    for _, row in sku_fc.iterrows():
                        predictions.append({
                            "week_commencing": row["date"].strftime("%Y-%m-%d"),
                            "predicted_units": int(row["predicted_demand"])
                        })
                        
                    artifact = joblib.load(model_path)
                    selected_model = artifact.get("comparison", {}).get("selected_model", "Unknown")
                    
                    self.send_json_response(200, {
                        "sku_id": sku_id,
                        "product_name": sku_risk["product"],
                        "selected_model": selected_model,
                        "horizon": "4 weeks",
                        "forecast": predictions
                    })
                else: # path == "/risk"
                    self.send_json_response(200, {
                        "sku_id": sku_id,
                        "product_name": sku_risk["product"],
                        "category": sku_risk["category"],
                        "subcategory": sku_risk["subcategory"],
                        "stock_level_on_hand": int(sku_risk["on_hand_units"]),
                        "on_order_units": int(sku_risk["on_order_units"]),
                        "days_of_coverage": round(sku_risk["days_of_cover"], 2),
                        "reorder_point": int(sku_risk["reorder_point"]),
                        "stockout_risk": sku_risk["stockout_risk"],
                        "overstock_risk": sku_risk["overstock_risk"],
                        "action_recommended": sku_risk["action"],
                        "action_rationale": sku_risk["recommendation"],
                        "financial_impact": {
                            "sales_at_risk_rupees": float(sku_risk["sales_at_risk"]),
                            "capital_locked_rupees": float(sku_risk["capital_locked"]),
                            "potential_excess_units": int(sku_risk["excess_units"])
                        }
                    })
            except Exception as e:
                self.send_json_response(500, {
                    "error": "Internal Server Error",
                    "message": f"Prediction scoring logic error: {e}"
                })
            return

        # 3. Path Not Found Fallback
        self.send_json_response(404, {
            "error": "Not Found",
            "message": "Endpoint not found. Valid endpoints are: GET /status, GET /predict?sku=<id>, GET /risk?sku=<id>"
        })


def run_api_server(port: int = 8000):
    """Start the zero-dependency HTTPServer API."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, ScoringAPIHandler)
    print(f"FORESIGHT Scoring API Service successfully listening on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server...")
        httpd.server_close()


if __name__ == "__main__":
    run_api_server()
