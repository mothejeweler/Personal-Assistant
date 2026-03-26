-- PostgreSQL Schema for Raj Backend

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20),
    instagram_username VARCHAR(100),
    tiktok_username VARCHAR(100),
    email VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    
    -- Preferences learned from conversations
    preferred_style VARCHAR(255),
    price_range VARCHAR(50),
    preferred_metal VARCHAR(50),
    
    -- Purchase history
    total_purchases DECIMAL(10, 2) DEFAULT 0,
    purchase_count INT DEFAULT 0,
    last_purchase_date TIMESTAMP,
    average_order_value DECIMAL(10, 2),
    
    -- Engagement
    lead_score INT DEFAULT 0,
    is_high_value BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_contacted_at TIMESTAMP,
    
    UNIQUE(phone, instagram_username, tiktok_username, email)
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    channel VARCHAR(50), -- 'whatsapp', 'instagram', 'tiktok', 'sms', 'web'
    external_message_id VARCHAR(255),
    
    direction VARCHAR(20), -- 'inbound', 'outbound'
    message_text TEXT,
    parsed_intent VARCHAR(255), -- e.g., 'inquiry', 'custom_design', 'complaint', 'purchase'
    sentiment VARCHAR(20), -- 'positive', 'neutral', 'negative'
    
    responded BOOLEAN DEFAULT FALSE,
    response_text TEXT,
    response_sent_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (customer_id, created_at),
    INDEX (channel, created_at),
    INDEX (parsed_intent)
);

CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE,
    design_name VARCHAR(255),
    style_category VARCHAR(100), -- e.g., 'burst', 'solitaire', 'chains', 'hip_hop'
    material VARCHAR(50), -- 'gold', 'silver', 'platinum'
    current_stock INT,
    reorder_level INT,
    
    shopify_product_id VARCHAR(100),
    shopify_variant_id VARCHAR(100),
    
    price_usd DECIMAL(10, 2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_alerts (
    id SERIAL PRIMARY KEY,
    inventory_id INT REFERENCES inventory(id),
    alert_type VARCHAR(50), -- 'low_stock', 'out_of_stock', 'overstock'
    message TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trends (
    id SERIAL PRIMARY KEY,
    hashtag VARCHAR(100),
    keyword VARCHAR(255),
    platform VARCHAR(50), -- 'instagram', 'tiktok', 'twitter'
    
    trend_category VARCHAR(100), -- e.g., 'hip_hop_jewelry', 'engagement_rings', 'custom_design'
    mention_count INT,
    engagement_rate DECIMAL(5, 2),
    
    relevance_to_mo BOOLEAN DEFAULT FALSE,
    recommended_action TEXT,
    
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (platform, created_at)
);

CREATE TABLE IF NOT EXISTS content_ideas (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50), -- 'dm_analysis', 'trend_spike', 'competitor_watch'
    idea_title VARCHAR(255),
    description TEXT,
    design_to_feature VARCHAR(255),
    estimated_reach INT,
    
    priority_score INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'published'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team_tasks (
    id SERIAL PRIMARY KEY,
    assigned_to VARCHAR(50), -- 'shiva', 'sujitha', 'mo'
    task_title VARCHAR(255),
    description TEXT,
    priority VARCHAR(20), -- 'high', 'medium', 'low'
    
    due_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
    
    escalation_attempts INT DEFAULT 0,
    last_reminder_sent TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_benchmarks (
    id SERIAL PRIMARY KEY,
    benchmark_date DATE,
    
    -- Engagement
    messages_received INT DEFAULT 0,
    messages_responded INT DEFAULT 0,
    avg_response_time_minutes INT DEFAULT 0,
    
    -- Sales
    high_intent_customers INT DEFAULT 0,
    quotes_sent INT DEFAULT 0,
    conversions INT DEFAULT 0,
    
    -- Inventory
    low_stock_alerts INT DEFAULT 0,
    items_restocked INT DEFAULT 0,
    
    -- Trends
    new_trends_detected INT DEFAULT 0,
    recommended_actions INT DEFAULT 0,
    
    -- Content
    content_published INT DEFAULT 0,
    engagement_rate DECIMAL(5, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(benchmark_date)
);

CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_conversations_customer_date ON conversations(customer_id, created_at DESC);
CREATE INDEX idx_conversations_channel ON conversations(channel, created_at DESC);
CREATE INDEX idx_inventory_stock ON inventory(current_stock);
CREATE INDEX idx_trends_platform_date ON trends(platform, created_at DESC);
CREATE INDEX idx_team_tasks_assigned ON team_tasks(assigned_to, status);
