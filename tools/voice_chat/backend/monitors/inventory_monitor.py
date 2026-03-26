"""
Inventory Monitor - Tracks stock levels and alerts on low inventory
"""

from sqlalchemy.orm import Session
from database.models import Inventory, InventoryAlert, SystemSettings, DailyBenchmark
from datetime import datetime, date
from integrations.shopify_sync import ShopifyClient

class InventoryMonitor:
    def __init__(self, db: Session):
        self.db = db
        self.shopify = ShopifyClient()
    
    def sync_shopify_inventory(self):
        """Pull latest inventory from Shopify"""
        print("[INVENTORY MONITOR] Syncing Shopify...")
        self.shopify.sync_to_database(self.db)
    
    def check_stock_levels(self) -> dict:
        """Check for low/out-of-stock items"""
        low_stock = self.db.query(Inventory).filter(
            Inventory.current_stock <= Inventory.reorder_level
        ).all()
        
        out_of_stock = self.db.query(Inventory).filter(
            Inventory.current_stock == 0
        ).all()
        
        alerts = []
        
        for item in low_stock:
            if item.current_stock > 0:
                alerts.append({
                    "type": "low_stock",
                    "design": item.design_name,
                    "sku": item.sku,
                    "current": item.current_stock,
                    "reorder_level": item.reorder_level,
                    "severity": "medium"
                })
        
        for item in out_of_stock:
            alerts.append({
                "type": "out_of_stock",
                "design": item.design_name,
                "sku": item.sku,
                "severity": "high"
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts
        }
    
    def create_alerts(self, alert_data: dict):
        """Store inventory alerts in database"""
        for alert in alert_data.get("alerts", []):
            inventory = self.db.query(Inventory).filter(
                Inventory.sku == alert["sku"]
            ).first()
            
            if inventory:
                # Check if we already have an unresolved alert for this
                existing_alert = self.db.query(InventoryAlert).filter(
                    InventoryAlert.inventory_id == inventory.id,
                    InventoryAlert.is_resolved == False
                ).first()
                
                if not existing_alert:
                    new_alert = InventoryAlert(
                        inventory_id=inventory.id,
                        alert_type=alert["type"],
                        message=f"{alert['design']} ({alert['sku']}) is {alert['type']}"
                    )
                    self.db.add(new_alert)
        
        self.db.commit()
        print(f"[INVENTORY MONITOR] Created alerts for {len(alert_data.get('alerts', []))} items")
    
    def update_daily_benchmark(self):
        """Update today's benchmark with inventory alerts"""
        today = date.today().isoformat()
        
        benchmark = self.db.query(DailyBenchmark).filter(
            DailyBenchmark.benchmark_date == today
        ).first()
        
        if not benchmark:
            benchmark = DailyBenchmark(benchmark_date=today)
            self.db.add(benchmark)
        
        # Count alerts created today
        today_alerts = self.db.query(InventoryAlert).filter(
            InventoryAlert.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
        
        benchmark.low_stock_alerts = today_alerts
        self.db.commit()
    
    def run_monitoring_cycle(self):
        """Full monitoring cycle: sync, check, create alerts"""
        print("[INVENTORY MONITOR] Starting cycle...")
        self.sync_shopify_inventory()
        alert_data = self.check_stock_levels()
        self.create_alerts(alert_data)
        self.update_daily_benchmark()
        print(f"[INVENTORY MONITOR] Found {alert_data['alerts_count']} alerts")
        return alert_data
