"""
DM Monitor - Analyzes incoming DMs to extract intent and score leads
"""

import os
import json
from datetime import datetime, date

from sqlalchemy.orm import Session
from database.models import Conversation, Customer, DailyBenchmark
from anthropic import Anthropic

client = Anthropic()
ANTHROPIC_ANALYSIS_MODEL = os.getenv("ANTHROPIC_ANALYSIS_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest"))

class DMMonitor:
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_unanalyzed_messages(self):
        """Analyze DMs that haven't been scored yet"""
        
        # Get unanalyzed messages (where intent is NULL)
        unanalyzed = self.db.query(Conversation).filter(
            Conversation.parsed_intent == None,
            Conversation.direction == "inbound"
        ).all()
        
        results = {
            "analyzed": 0,
            "insights": []
        }
        
        for msg in unanalyzed:
            analysis = self._analyze_message(msg.message_text)
            
            msg.parsed_intent = analysis.get("intent")
            msg.sentiment = analysis.get("sentiment")
            
            # Update customer lead score based on intent
            if analysis.get("intent") == "purchase_interest":
                msg.customer.lead_score += 15
            elif analysis.get("intent") == "custom_design":
                msg.customer.lead_score += 20
            elif analysis.get("intent") == "complaint":
                msg.customer.lead_score -= 10
            
            results["analyzed"] += 1
            results["insights"].append({
                "customer": msg.customer.first_name,
                "intent": analysis.get("intent"),
                "sentiment": analysis.get("sentiment")
            })
        
        self.db.commit()
        return results
    
    def _analyze_message(self, message_text: str) -> dict:
        """Use Claude to analyze a single message"""
        try:
            response = client.messages.create(
                model=ANTHROPIC_ANALYSIS_MODEL,
                max_tokens=200,
                system="""You are a jewelry sales analyst. Analyze the customer message and determine:
1. Intent: 'inquiry', 'purchase_interest', 'custom_design', 'complaint', 'follow_up', 'other'
2. Sentiment: 'positive', 'neutral', 'negative'
3. Urgency: 'high', 'medium', 'low'

Respond in JSON format: {"intent": "...", "sentiment": "...", "urgency": "..."}""",
                messages=[
                    {"role": "user", "content": message_text}
                ]
            )
            
            response_text = response.content[0].text
            # Parse JSON response
            return json.loads(response_text)
        except Exception as e:
            print(f"Error analyzing message: {e}")
            return {
                "intent": "other",
                "sentiment": "neutral",
                "urgency": "medium"
            }
    
    def identify_high_intent_customers(self):
        """Identify customers ready to buy and update their lead scores"""
        
        # Get customers with positive sentiment and purchase-related intents
        conversations = self.db.query(Conversation).filter(
            Conversation.sentiment.in_(["positive", "neutral"]),
            Conversation.parsed_intent.in_(["purchase_interest", "custom_design"])
        ).all()
        
        customer_scores = {}
        
        for conv in conversations:
            cid = conv.customer_id
            if cid not in customer_scores:
                customer_scores[cid] = 0
            
            if conv.parsed_intent == "custom_design":
                customer_scores[cid] += 25
            elif conv.parsed_intent == "purchase_interest":
                customer_scores[cid] += 15
            
            if conv.sentiment == "positive":
                customer_scores[cid] += 10
        
        # Update customer records
        for customer_id, score_increase in customer_scores.items():
            customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
            if customer:
                customer.lead_score = min(100, customer.lead_score + score_increase)
                if customer.lead_score >= 75:
                    customer.is_high_value = True
        
        self.db.commit()
        
        return {
            "customers_analyzed": len(customer_scores),
            "high_intent_customers": len([c for c in customer_scores.values() if c >= 75])
        }
    
    def extract_content_ideas(self):
        """Extract content ideas from DM patterns"""
        
        # Find most common questions/interests
        intents = self.db.query(Conversation.parsed_intent).filter(
            Conversation.parsed_intent != None
        ).group_by(Conversation.parsed_intent).count()
        
        # This is a simplified version - real implementation would cluster similar messages
        return {"ideas_extracted": 0}
    
    def update_daily_benchmark(self):
        """Update daily benchmark with DM analytics"""
        today = date.today().isoformat()
        
        benchmark = self.db.query(DailyBenchmark).filter(
            DailyBenchmark.benchmark_date == today
        ).first()
        
        if not benchmark:
            benchmark = DailyBenchmark(benchmark_date=today)
            self.db.add(benchmark)
        
        # Count messages
        messages_received = self.db.query(Conversation).filter(
            Conversation.direction == "inbound",
            Conversation.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
        
        messages_responded = self.db.query(Conversation).filter(
            Conversation.direction == "outbound",
            Conversation.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
        
        high_intent = self.db.query(Customer).filter(
            Customer.lead_score >= 75
        ).count()
        
        benchmark.messages_received = messages_received
        benchmark.messages_responded = messages_responded
        benchmark.high_intent_customers = high_intent
        
        self.db.commit()
    
    def run_monitoring_cycle(self):
        """Full DM analysis cycle"""
        print("[DM MONITOR] Starting cycle...")
        
        analysis = self.analyze_unanalyzed_messages()
        high_intent = self.identify_high_intent_customers()
        self.update_daily_benchmark()
        
        print(f"[DM MONITOR] Analyzed {analysis['analyzed']} messages")
        print(f"[DM MONITOR] {high_intent['high_intent_customers']} high-intent customers identified")
        
        return {
            "messages_analyzed": analysis["analyzed"],
            "high_intent_customers": high_intent["high_intent_customers"]
        }
