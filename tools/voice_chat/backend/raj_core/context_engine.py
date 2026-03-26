"""
Raj Context Engine
Orchestrates all the data Raj needs to be intelligent:
- Customer history
- Current inventory status
- Trending topics
- Recent interactions
- Business priorities
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import (
    Customer, Conversation, Inventory, Trend, 
    ContentIdea, TeamTask, DailyBenchmark
)
from raj_core.personality import (
    get_system_prompt, get_customer_context_prompt,
    get_trend_injection, get_inventory_context
)
import json

class RajContextEngine:
    def __init__(self, db: Session):
        self.db = db
    
    def get_customer_by_phone(self, phone: str) -> dict:
        """Retrieve customer by phone number and their conversation history"""
        customer = self.db.query(Customer).filter(Customer.phone == phone).first()
        if not customer:
            return None
        
        # Get last 10 conversations
        recent_convos = self.db.query(Conversation).filter(
            Conversation.customer_id == customer.id
        ).order_by(Conversation.created_at.desc()).limit(10).all()
        
        return {
            "id": customer.id,
            "first_name": customer.first_name,
            "phone": customer.phone,
            "previous_purchases": [c.message_text for c in recent_convos if c.direction == "outbound"],
            "preferred_style": customer.preferred_style,
            "price_range": customer.price_range,
            "lead_score": customer.lead_score,
            "total_purchases": float(customer.total_purchases) if customer.total_purchases else 0,
            "last_contacted": customer.last_contacted_at.isoformat() if customer.last_contacted_at else None,
            "recent_conversation": [
                {
                    "date": c.created_at.isoformat(),
                    "message": c.message_text,
                    "intent": c.parsed_intent,
                    "sentiment": c.sentiment
                } for c in recent_convos[:5]
            ]
        }
    
    def get_customer_by_instagram(self, username: str) -> dict:
        """Retrieve customer by Instagram username"""
        customer = self.db.query(Customer).filter(
            Customer.instagram_username == username
        ).first()
        if customer:
            return self.get_customer_by_phone(customer.phone)
        return None
    
    def get_trending_now(self, limit: int = 5) -> list:
        """Get the hottest trends right now, especially hip hop jewelry"""
        # Filter for trends from last 24 hours with high engagement
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        trends = self.db.query(Trend).filter(
            Trend.last_checked >= cutoff_time,
            Trend.relevance_to_mo == True
        ).order_by(
            Trend.engagement_rate.desc(),
            Trend.mention_count.desc()
        ).limit(limit).all()
        
        return [
            {
                "keyword": t.keyword,
                "platform": t.platform,
                "mention_count": t.mention_count,
                "engagement_rate": float(t.engagement_rate) if t.engagement_rate else 0,
                "recommendation": t.recommended_action,
                "category": t.trend_category
            } for t in trends
        ]
    
    def get_inventory_status(self) -> dict:
        """Get current inventory with alerts"""
        low_stock = self.db.query(Inventory).filter(
            Inventory.current_stock <= Inventory.reorder_level
        ).all()
        
        out_of_stock = self.db.query(Inventory).filter(
            Inventory.current_stock == 0
        ).all()
        
        bestsellers = self.db.query(Inventory).order_by(
            Inventory.current_stock.desc()
        ).limit(5).all()
        
        return {
            "low_stock_items": [
                {
                    "design_name": i.design_name,
                    "current_stock": i.current_stock,
                    "sku": i.sku,
                    "style": i.style_category,
                    "status": "LOW" if i.current_stock > 0 else "OUT"
                } for i in low_stock + out_of_stock
            ],
            "bestsellers": [
                {
                    "design_name": i.design_name,
                    "current_stock": i.current_stock,
                    "style": i.style_category
                } for i in bestsellers
            ]
        }
    
    def get_high_intent_customers(self) -> list:
        """Get customers who are likely to buy soon"""
        high_intent = self.db.query(Customer).filter(
            Customer.lead_score >= 75
        ).order_by(Customer.lead_score.desc()).limit(10).all()
        
        return [
            {
                "name": f"{c.first_name} {c.last_name}",
                "phone": c.phone,
                "lead_score": c.lead_score,
                "reason": "Ready to purchase" if c.lead_score >= 85 else "Warm lead"
            } for c in high_intent
        ]
    
    def get_content_roadmap(self) -> list:
        """Get suggested content ideas based on trends and DM analysis"""
        ideas = self.db.query(ContentIdea).filter(
            ContentIdea.status == 'pending'
        ).order_by(ContentIdea.priority_score.desc()).limit(5).all()
        
        return [
            {
                "title": i.idea_title,
                "description": i.description,
                "design_to_feature": i.design_to_feature,
                "source": i.source_type,
                "priority": i.priority_score
            } for i in ideas
        ]
    
    def get_team_tasks(self) -> dict:
        """Get pending tasks for Shiva and Sujitha"""
        shiva_tasks = self.db.query(TeamTask).filter(
            TeamTask.assigned_to == 'shiva',
            TeamTask.status == 'pending'
        ).order_by(TeamTask.priority.desc()).all()
        
        sujitha_tasks = self.db.query(TeamTask).filter(
            TeamTask.assigned_to == 'sujitha',
            TeamTask.status == 'pending'
        ).order_by(TeamTask.priority.desc()).all()
        
        return {
            "shiva": [
                {
                    "task": t.task_title,
                    "priority": t.priority,
                    "due": t.due_date.isoformat() if t.due_date else None
                } for t in shiva_tasks
            ],
            "sujitha": [
                {
                    "task": t.task_title,
                    "priority": t.priority,
                    "due": t.due_date.isoformat() if t.due_date else None
                } for t in sujitha_tasks
            ]
        }
    
    def get_daily_standup(self) -> dict:
        """Generate Mo's daily morning briefing"""
        today = datetime.now().strftime('%Y-%m-%d')
        benchmark = self.db.query(DailyBenchmark).filter(
            DailyBenchmark.benchmark_date == today
        ).first()
        
        if not benchmark:
            return {"status": "No data yet for today"}
        
        return {
            "messages_received": benchmark.messages_received,
            "messages_responded": benchmark.messages_responded,
            "high_intent_customers": benchmark.high_intent_customers,
            "low_stock_alerts": benchmark.low_stock_alerts,
            "new_trends": benchmark.new_trends_detected,
            "content_published": benchmark.content_published,
            "conversions": benchmark.conversions
        }
    
    def build_full_context(self, customer_data: dict = None, include_trends: bool = True) -> str:
        """
        Build a complete context string to inject into Raj's system prompt.
        This is what tells Raj what to know about right now.
        """
        context_parts = []
        
        # Customer-specific context
        if customer_data:
            context_parts.append(get_customer_context_prompt(customer_data))
        
        # Current trends (hip hop jewelry, etc.)
        if include_trends:
            trends = self.get_trending_now()
            if trends:
                context_parts.append(get_trend_injection(trends))
        
        # Inventory alerts
        inventory = self.get_inventory_status()
        if inventory.get("low_stock_items"):
            context_parts.append(get_inventory_context(inventory["low_stock_items"]))
        
        # High-intent customers alert
        high_intent = self.get_high_intent_customers()
        if high_intent and len(high_intent) > 0:
            context_parts.append(f"\n[PRIORITY CUSTOMERS]\n⭐ {len(high_intent)} customers ready to buy soon")
        
        return "\n".join([p for p in context_parts if p])
    
    def create_or_update_customer(self, phone: str = None, instagram: str = None, 
                                  first_name: str = None, last_name: str = None) -> Customer:
        """Create or update a customer record"""
        customer = None
        
        if phone:
            customer = self.db.query(Customer).filter(Customer.phone == phone).first()
        elif instagram:
            customer = self.db.query(Customer).filter(
                Customer.instagram_username == instagram
            ).first()
        
        if not customer:
            customer = Customer(
                phone=phone,
                instagram_username=instagram,
                first_name=first_name,
                last_name=last_name
            )
            self.db.add(customer)
        else:
            if first_name:
                customer.first_name = first_name
            if last_name:
                customer.last_name = last_name
        
        self.db.commit()
        return customer
    
    def log_conversation(self, customer_id: int, channel: str, message: str, 
                        direction: str = "inbound", intent: str = None, 
                        sentiment: str = None, response_by: str = 'raj') -> Conversation:
        """Log a conversation message"""
        conversation = Conversation(
            customer_id=customer_id,
            channel=channel,
            message_text=message,
            direction=direction,
            parsed_intent=intent,
            sentiment=sentiment,
            response_by=response_by
        )
        self.db.add(conversation)
        self.db.commit()
        return conversation
