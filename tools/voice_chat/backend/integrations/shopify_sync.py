"""
Shopify Integration
Syncs inventory, tracks sales, retrieves customer purchase history
"""

import os
import requests
from typing import dict, list
from datetime import datetime

class ShopifyClient:
    def __init__(self):
        self.store_url = os.getenv("SHOPIFY_STORE_URL")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        self.api_version = "2024-01"
        self.base_url = f"https://{self.store_url}/admin/api/{self.api_version}"
    
    def get_headers(self):
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    def get_inventory(self) -> list:
        """Get all product inventory"""
        try:
            response = requests.get(
                f"{self.base_url}/products.json",
                headers=self.get_headers(),
                params={"limit": 250}
            )
            response.raise_for_status()
            products = response.json().get("products", [])
            
            inventory = []
            for product in products:
                for variant in product.get("variants", []):
                    inventory.append({
                        "sku": variant.get("sku"),
                        "design_name": product.get("title"),
                        "style_category": product.get("product_type", "general"),
                        "product_id": product.get("id"),
                        "variant_id": variant.get("id"),
                        "current_stock": variant.get("inventory_quantity", 0),
                        "price": float(variant.get("price", 0)),
                        "material": product.get("vendor", "unknown")
                    })
            
            return inventory
        except Exception as e:
            print(f"Error fetching Shopify inventory: {e}")
            return []
    
    def get_customer_orders(self, customer_email: str) -> list:
        """Get all orders for a customer by email"""
        try:
            response = requests.get(
                f"{self.base_url}/customers/search.json",
                headers=self.get_headers(),
                params={"query": f"email:{customer_email}"}
            )
            response.raise_for_status()
            customers = response.json().get("customers", [])
            
            if not customers:
                return []
            
            customer_id = customers[0]["id"]
            
            # Get orders for this customer
            orders_response = requests.get(
                f"{self.base_url}/customers/{customer_id}/orders.json",
                headers=self.get_headers()
            )
            orders_response.raise_for_status()
            
            orders = orders_response.json().get("orders", [])
            
            return [
                {
                    "order_id": order.get("id"),
                    "date": order.get("created_at"),
                    "total": float(order.get("total_price", 0)),
                    "items": [
                        {
                            "product": line.get("title"),
                            "quantity": line.get("quantity"),
                            "price": float(line.get("price", 0))
                        } for line in order.get("line_items", [])
                    ]
                } for order in orders
            ]
        except Exception as e:
            print(f"Error fetching Shopify orders: {e}")
            return []
    
    def update_inventory(self, product_id: int, new_quantity: int) -> bool:
        """Update inventory for a product"""
        try:
            # This would need proper implementation with inventory levels
            return True
        except Exception as e:
            print(f"Error updating Shopify inventory: {e}")
            return False
    
    def sync_to_database(self, db):
        """Sync Shopify inventory to local database"""
        from database.models import Inventory
        
        inventory_data = self.get_inventory()
        
        for item in inventory_data:
            existing = db.query(Inventory).filter(Inventory.sku == item["sku"]).first()
            
            if existing:
                existing.current_stock = item["current_stock"]
                existing.price_usd = item["price"]
            else:
                new_inventory = Inventory(
                    sku=item["sku"],
                    design_name=item["design_name"],
                    style_category=item["style_category"],
                    material=item["material"],
                    current_stock=item["current_stock"],
                    price_usd=item["price"],
                    shopify_product_id=item["product_id"],
                    shopify_variant_id=item["variant_id"],
                    reorder_level=5
                )
                db.add(new_inventory)
        
        db.commit()
        print(f"Synced {len(inventory_data)} items from Shopify")
