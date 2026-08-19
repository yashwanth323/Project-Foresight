"""Unit tests for FORESIGHT forecasting logic, risk engines, and WAPE metrics."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path to enable importing src modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import unittest
import numpy as np
import pandas as pd
import joblib

from src.forecast import calculate_wape, calculate_bias, seasonal_naive_forecast
from src.risk import score_inventory_risk, RISK_CONFIG


class TestForesightLogic(unittest.TestCase):
    """Test cases for metrics, forecasts, and inventory risk equations."""
    
    def test_wape_calculation(self):
        """Test the WAPE equation on simple targets."""
        actual = [100, 200, 150]
        predicted = [90, 220, 140]
        
        # sum(|actual - pred|) = 10 + 20 + 10 = 40
        # sum(actual) = 450
        # WAPE = 40 / 450 = 0.08888...
        expected_wape = 40.0 / 450.0
        self.assertAlmostEqual(calculate_wape(actual, predicted), expected_wape)
        
        # Test zero denominator fallback
        self.assertEqual(calculate_wape([0, 0], [10, 10]), 0.0)

    def test_bias_calculation(self):
        """Test the normalized forecast bias equation."""
        actual = [100, 200, 150]
        predicted = [90, 220, 140]
        
        # sum(pred - actual) = -10 + 20 - 10 = 0
        # Bias = 0 / 450 = 0.0
        self.assertEqual(calculate_bias(actual, predicted), 0.0)

    def test_seasonal_naive_forecast(self):
        """Test that seasonal naive repeats the previous cycle's values."""
        # Create a small dataset with 8 weeks of history for one SKU
        dates = pd.date_range("2026-01-01", periods=8, freq="W")
        history = pd.DataFrame({
            "sku_id": ["TEST-SKU"] * 8,
            "sku": ["TEST-SKU"] * 8,
            "product": ["Test Product"] * 8,
            "category": ["Test Cat"] * 8,
            "subcategory": ["Test Sub"] * 8,
            "date": dates,
            "units_sold": [10, 20, 30, 40, 10, 20, 30, 40], # Monthly pattern (period=4)
            "current_stock": [100] * 8,
            "unit_cost": [5.0] * 8,
            "list_price": [10.0] * 8,
            "price": [10.0] * 8
        })
        
        # Predict 4 weeks horizon, seasonal period = 4
        fc = seasonal_naive_forecast(history, horizon_weeks=4, seasonal_period_weeks=4)
        
        # Forecast should repeat the last 4 actuals: [10, 20, 30, 40]
        self.assertEqual(len(fc), 4)
        self.assertEqual(fc["predicted_demand"].tolist(), [10.0, 20.0, 30.0, 40.0])
        self.assertEqual(fc["sku_id"].tolist(), ["TEST-SKU"] * 4)

    def test_risk_scoring_and_rupee_impact(self):
        """Test stockout/overstock scoring logic and Rupee business impact metrics."""
        # Setup forecast predictions over 4 weeks for one SKU
        dates = pd.date_range("2026-06-01", periods=4, freq="W")
        forecast_df = pd.DataFrame({
            "sku_id": ["SKU-A"] * 4,
            "product": ["Product A"] * 4,
            "category": ["Category A"] * 4,
            "subcategory": ["Subcat A"] * 4,
            "date": dates,
            "predicted_demand": [70, 70, 70, 70], # 70 units/week. Average daily = 10 units/day.
            "on_hand_units": [20.0] * 4, # Low stock on hand
            "on_order_units": [0.0] * 4,
            "lead_time_days": [7.0] * 4, # 7 days lead time. ROP = 10 * (7 + 3) = 100.
            "unit_cost": [50.0] * 4,
            "price": [100.0] * 4
        })
        
        risks = score_inventory_risk(forecast_df)
        sku_risk = risks[risks["sku_id"] == "SKU-A"].iloc[0]
        
        # Lead time demand = 70 units over 7 days (10 units/day * 7)
        # Available stock = 20. Stockout risk trigger is activated (20 < 70)
        self.assertEqual(sku_risk["action"], "REORDER NOW")
        self.assertEqual(sku_risk["recommended_order"], 80) # ROP(100) - Available(20) = 80
        
        # Shortage = Lead Time Demand (70) - Available Stock (20) = 50 units
        # Sales at Risk = 50 * 100 = 5,000
        self.assertAlmostEqual(sku_risk["sales_at_risk"], 5000.0)
        
        # Excess units should be 0 since stock is low
        self.assertEqual(sku_risk["excess_units"], 0.0)
        self.assertEqual(sku_risk["capital_locked"], 0.0)

    def test_model_selection_not_none(self):
        """Regression test: verify train_forecast_model returns valid dict and never None."""
        from src.forecast import train_forecast_model, FEATURES
        import tempfile
        
        # Create a valid weekly DataFrame with enough history to support backtesting
        dates = pd.date_range("2025-01-01", periods=25, freq="W")
        df = pd.DataFrame({
            "sku_id": ["SKU-A"] * 25,
            "sku": ["SKU-A"] * 25,
            "product": ["Product A"] * 25,
            "category": ["Category A"] * 25,
            "subcategory": ["Subcat A"] * 25,
            "date": dates,
            "units_sold": [10 + i for i in range(25)],
            "current_stock": [100] * 25,
            "unit_cost": [10.0] * 25,
            "list_price": [20.0] * 25,
            "price": [20.0] * 25,
            "week_of_year": [d.week for d in dates],
            "month": [d.month for d in dates],
            "season": [d.month % 12 // 3 + 1 for d in dates],
            "is_holiday": [0] * 25,
            "promo_flag": [0] * 25
        })
        
        # Populate all FEATURES columns
        for f in FEATURES:
            if f not in df.columns:
                df[f] = 1.0
                
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model_temp.pkl"
            
            # Execute model training/selection
            model, comp_metrics = train_forecast_model(df, model_path, seasonal_period_weeks=4)
            
            # Assertions
            self.assertIsNotNone(comp_metrics, "comp_metrics should not be None")
            self.assertIsInstance(comp_metrics, dict, "comp_metrics must be a dict")
            self.assertIn("selected_model", comp_metrics)
            self.assertIn("selected_wape", comp_metrics)
            self.assertIn("selected_bias", comp_metrics)
            self.assertIn("Random Forest", comp_metrics)
            self.assertIn("Seasonal Naive", comp_metrics)
            
            # Check model dictionary keys saved on disk
            self.assertTrue(model_path.exists(), "Model file should be saved on disk")
            saved_artifact = joblib.load(model_path)
            self.assertIsInstance(saved_artifact, dict, "Saved model artifact must be a dict")
            self.assertIn("model", saved_artifact)
            self.assertIn("comparison", saved_artifact)
            self.assertIsNotNone(saved_artifact["comparison"], "Saved comparison metrics should not be None")

    def test_forecast_output_schema(self):
        """Regression test: verify forecast_next_days outputs contain essential business-facing columns."""
        from src.forecast import train_forecast_model, forecast_next_days, FEATURES
        import tempfile
        
        dates = pd.date_range("2025-01-01", periods=25, freq="W")
        df = pd.DataFrame({
            "sku_id": ["SKU-A"] * 25,
            "sku": ["SKU-A"] * 25,
            "product": ["Product A"] * 25,
            "category": ["Category A"] * 25,
            "subcategory": ["Subcat A"] * 25,
            "date": dates,
            "units_sold": [10 + i for i in range(25)],
            "current_stock": [100] * 25,
            "on_hand_units": [100.0] * 25,
            "on_order_units": [0.0] * 25,
            "lead_time_days": [7.0] * 25,
            "reorder_point": [50.0] * 25,
            "unit_cost": [10.0] * 25,
            "list_price": [20.0] * 25,
            "price": [20.0] * 25,
            "week_of_year": [d.week for d in dates],
            "month": [d.month for d in dates],
            "season": [d.month % 12 // 3 + 1 for d in dates],
            "is_holiday": [0] * 25,
            "promo_flag": [0] * 25
        })
        
        for f in FEATURES:
            if f not in df.columns:
                df[f] = 1.0
                
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model_temp.pkl"
            
            # 1. Test Seasonal Naive path
            comparison_sn = {
                "selected_model": "Seasonal Naive",
                "selected_wape": 0.1,
                "selected_bias": 0.01,
                "seasonal_period_weeks": 4
            }
            artifact_sn = {
                "model": None,
                "features": FEATURES,
                "comparison": comparison_sn
            }
            joblib.dump(artifact_sn, model_path)
            
            fc_sn = forecast_next_days(df, model_path, horizon=4)
            
            required_business_cols = ["date", "sku_id", "product", "predicted_demand", "price", "current_stock"]
            for col in required_business_cols:
                self.assertIn(col, fc_sn.columns, f"Seasonal Naive forecast missing required business column: {col}")
                
            # 2. Test Random Forest path
            train_forecast_model(df, model_path, seasonal_period_weeks=4)
            comparison_rf = {
                "selected_model": "Random Forest",
                "selected_wape": 0.05,
                "selected_bias": -0.01,
                "seasonal_period_weeks": 4
            }
            artifact_rf = {
                "model": joblib.load(model_path)["model"],
                "features": FEATURES,
                "comparison": comparison_rf
            }
            joblib.dump(artifact_rf, model_path)
            
            fc_rf = forecast_next_days(df, model_path, horizon=4)
            
            for col in required_business_cols:
                self.assertIn(col, fc_rf.columns, f"Random Forest forecast missing required business column: {col}")


class TestForesightAuth(unittest.TestCase):
    """Test cases for registration, role security, password hashing, and login verification."""
    
    def setUp(self):
        import tempfile
        import auth.users
        
        # Backup original database path and create an isolated temp test database
        self.original_json_path = auth.users.USERS_JSON_PATH
        self.test_dir = tempfile.TemporaryDirectory()
        auth.users.USERS_JSON_PATH = Path(self.test_dir.name) / "users_test.json"
        
        # Load test database with default users
        default_users = auth.users.get_default_users()
        auth.users.save_users(default_users)

    def tearDown(self):
        import auth.users
        auth.users.USERS_JSON_PATH = self.original_json_path
        self.test_dir.cleanup()

    def test_default_logins(self):
        """1. Test that the three default accounts verify successfully."""
        from auth.users import verify_credentials
        
        # Administrator
        admin = verify_credentials("admin@foresight.ai", "admin123")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["username"], "Administrator")
        self.assertEqual(admin["role"], "Administrator")
        
        # Planner
        planner = verify_credentials("planner@foresight.ai", "planner123")
        self.assertIsNotNone(planner)
        self.assertEqual(planner["username"], "Planner")
        
        # Viewer
        viewer = verify_credentials("viewer@foresight.ai", "viewer123")
        self.assertIsNotNone(viewer)
        self.assertEqual(viewer["username"], "Viewer")
        
        # Test case-insensitivity and username login support
        admin_by_name = verify_credentials("Administrator", "admin123")
        self.assertIsNotNone(admin_by_name)
        self.assertEqual(admin_by_name["email"], "admin@foresight.ai")

    def test_new_user_registration_and_login(self):
        """2. Test registration, role default, hashing, duplicate prevention, and login validation."""
        from auth.users import register_new_user, verify_credentials
        
        # Register a valid new Planner
        success, msg = register_new_user("New Planner", "new_planner@foresight.ai", "securePass123", "Inventory Planner")
        self.assertTrue(success)
        
        # Verify new user can log in
        user = verify_credentials("new_planner@foresight.ai", "securePass123")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "New Planner")
        self.assertEqual(user["role"], "Inventory Planner")
        
        # Verify duplicate username rejection
        success, msg = register_new_user("New Planner", "other_email@foresight.ai", "password123", "Inventory Planner")
        self.assertFalse(success)
        self.assertEqual(msg, "Username is already taken.")
        
        # Verify duplicate email rejection
        success, msg = register_new_user("Other Planner", "new_planner@foresight.ai", "password123", "Inventory Planner")
        self.assertFalse(success)
        self.assertEqual(msg, "Email address is already registered.")

    def test_registration_validations_and_security(self):
        """3. Test field completion, email format, password length, and admin role security."""
        from auth.users import register_new_user
        
        # Empty fields
        success, msg = register_new_user("", "test@test.com", "password", "Inventory Planner")
        self.assertFalse(success)
        
        # Invalid email format
        success, msg = register_new_user("User1", "invalid_email_format", "password", "Inventory Planner")
        self.assertFalse(success)
        self.assertEqual(msg, "Invalid email address format.")
        
        # Weak password (length < 6)
        success, msg = register_new_user("User2", "user2@test.com", "12345", "Inventory Planner")
        self.assertFalse(success)
        self.assertEqual(msg, "Password must be at least 6 characters long.")
        
        # Role Security - new user cannot sign up as Administrator
        success, msg = register_new_user("Hacker Admin", "hacker@foresight.ai", "password123", "Administrator")
        self.assertFalse(success)
        self.assertEqual(msg, "Administrator account creation is restricted.")


if __name__ == "__main__":
    unittest.main()
