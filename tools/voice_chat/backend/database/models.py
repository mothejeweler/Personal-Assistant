from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mo:password@localhost:5432/raj_db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=True)
    instagram_username = Column(String(100), unique=True, nullable=True)
    tiktok_username = Column(String(100), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    preferred_style = Column(String(255))
    price_range = Column(String(50))
    preferred_metal = Column(String(50))
    
    total_purchases = Column(Numeric(10, 2), default=0)
    purchase_count = Column(Integer, default=0)
    last_purchase_date = Column(DateTime, nullable=True)
    average_order_value = Column(Numeric(10, 2), nullable=True)
    
    lead_score = Column(Integer, default=0)
    is_high_value = Column(Boolean, default=False)
    
    # Ownership & automation settings
    is_personal = Column(Boolean, default=False)  # True = Mo only, Raj never responds
    raj_can_respond = Column(Boolean, default=True)  # False = temporarily paused (override)
    first_contact_flagged = Column(Boolean, default=False)  # True = awaiting Mo's approval for new channels
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contacted_at = Column(DateTime, nullable=True)
    
    conversations = relationship("Conversation", back_populates="customer")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    channel = Column(String(50))  # 'whatsapp', 'instagram', 'tiktok', 'sms', 'web'
    external_message_id = Column(String(255), unique=True, nullable=True)
    
    direction = Column(String(20))  # 'inbound', 'outbound'
    message_text = Column(Text)
    parsed_intent = Column(String(255))  # 'inquiry', 'custom_design', 'complaint', 'purchase'
    sentiment = Column(String(20))  # 'positive', 'neutral', 'negative'
    
    # Response tracking
    responded = Column(Boolean, default=False)
    response_text = Column(Text, nullable=True)
    response_sent_at = Column(DateTime, nullable=True)
    response_by = Column(String(20), default='raj')  # 'raj' or 'mo'
    
    # Override tracking
    mo_override = Column(Boolean, default=False)  # True = Mo took over
    override_at = Column(DateTime, nullable=True)  # When Mo overrode
    auto_resume_at = Column(DateTime, nullable=True)  # When Raj can resume (24h from override)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="conversations")
    
    __table_args__ = (
        Index('idx_conversations_customer_date', 'customer_id', 'created_at'),
        Index('idx_conversations_channel', 'channel', 'created_at'),
    )

class FirstContactRequest(Base):
    """Tracks new customer first contacts that need Mo's approval"""
    __tablename__ = "first_contact_requests"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    channel = Column(String(50))  # 'instagram', 'tiktok', 'messenger'
    message_preview = Column(Text)  # First message from customer
    
    status = Column(String(50), default='pending')  # 'pending', 'approved', 'rejected'
    mo_decision_at = Column(DateTime, nullable=True)
    mo_decision = Column(String(20), nullable=True)  # 'raj' or 'mo'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    customer = relationship("Customer")

class MessageQueue(Base):
    """Queue for delayed responses to make Raj seem human-like (1-5min delay)"""
    __tablename__ = "message_queue"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    channel = Column(String(50))  # 'whatsapp', 'instagram', 'tiktok', etc
    message_text = Column(Text)  # The response message to send
    
    status = Column(String(50), default='queued')  # 'queued', 'sent', 'failed', 'urgency_skip'
    
    # Delay tracking
    queued_at = Column(DateTime, default=datetime.utcnow)
    scheduled_send_at = Column(DateTime)  # When to send (queued_at + 1-5min delay)
    sent_at = Column(DateTime, nullable=True)
    
    # Urgency detection
    is_urgent = Column(Boolean, default=False)  # Double/triple text = urgent
    consecutive_message_count = Column(Integer, default=1)  # How many messages in a row?
    last_customer_message_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = relationship("Customer")

class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), unique=True)
    design_name = Column(String(255))
    style_category = Column(String(100))  # 'burst', 'solitaire', 'chains', 'hip_hop'
    material = Column(String(50))  # 'gold', 'silver', 'platinum'
    current_stock = Column(Integer)
    reorder_level = Column(Integer)
    
    shopify_product_id = Column(String(100))
    shopify_variant_id = Column(String(100))
    
    price_usd = Column(Numeric(10, 2))
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    alerts = relationship("InventoryAlert", back_populates="inventory")

class InventoryAlert(Base):
    __tablename__ = "inventory_alerts"
    
    id = Column(Integer, primary_key=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"))
    alert_type = Column(String(50))  # 'low_stock', 'out_of_stock', 'overstock'
    message = Column(Text)
    is_resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    inventory = relationship("Inventory", back_populates="alerts")

class Trend(Base):
    __tablename__ = "trends"
    
    id = Column(Integer, primary_key=True)
    hashtag = Column(String(100))
    keyword = Column(String(255))
    platform = Column(String(50))  # 'instagram', 'tiktok', 'twitter'
    
    trend_category = Column(String(100))
    mention_count = Column(Integer)
    engagement_rate = Column(Numeric(5, 2))
    
    relevance_to_mo = Column(Boolean, default=False)
    recommended_action = Column(Text)
    
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentIdea(Base):
    __tablename__ = "content_ideas"
    
    id = Column(Integer, primary_key=True)
    source_type = Column(String(50))  # 'dm_analysis', 'trend_spike', 'competitor_watch'
    idea_title = Column(String(255))
    description = Column(Text)
    design_to_feature = Column(String(255))
    estimated_reach = Column(Integer)
    
    priority_score = Column(Integer, default=0)
    status = Column(String(50), default='pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

class TeamTask(Base):
    __tablename__ = "team_tasks"
    
    id = Column(Integer, primary_key=True)
    assigned_to = Column(String(50))  # 'shiva', 'sujitha', 'mo'
    task_title = Column(String(255))
    description = Column(Text)
    priority = Column(String(20))  # 'high', 'medium', 'low'
    
    due_date = Column(DateTime, nullable=True)
    status = Column(String(50), default='pending')
    
    escalation_attempts = Column(Integer, default=0)
    last_reminder_sent = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class DailyBenchmark(Base):
    __tablename__ = "daily_benchmarks"
    
    id = Column(Integer, primary_key=True)
    benchmark_date = Column(String(10), unique=True)  # YYYY-MM-DD
    
    messages_received = Column(Integer, default=0)
    messages_responded = Column(Integer, default=0)
    avg_response_time_minutes = Column(Integer, default=0)
    
    high_intent_customers = Column(Integer, default=0)
    quotes_sent = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    
    low_stock_alerts = Column(Integer, default=0)
    items_restocked = Column(Integer, default=0)
    
    new_trends_detected = Column(Integer, default=0)
    recommended_actions = Column(Integer, default=0)
    
    content_published = Column(Integer, default=0)
    engagement_rate = Column(Numeric(5, 2), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True)
    setting_value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
