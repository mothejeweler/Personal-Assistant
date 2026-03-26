"""
Trend Monitor - Continuously checks TikTok, Instagram for jewelry trends
Specifically tracks hip hop jewelry and luxury jewelry trends
"""

import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import Trend, ContentIdea
from raj_core.context_engine import RajContextEngine

class TrendMonitor:
    def __init__(self, db: Session):
        self.db = db
        self.tavily_api_key = __import__('os').getenv("TAVILY_API_KEY")
    
    def check_trends(self) -> dict:
        """Check current jewelry trends on social platforms"""
        
        keywords = [
            "hip hop jewelry",
            "burst diamond",
            "custom jewelry",
            "engagement rings trending",
            "celebrity jewelry TikTok",
            "luxury jewelry Instagram",
            "gold chains trending",
            "diamond rings viral",
            "jewelry TikTok trend",
            "men's jewelry viral"
        ]
        
        trends_found = []
        
        for keyword in keywords:
            trend_data = self._search_trend(keyword)
            if trend_data:
                trends_found.append(trend_data)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "trends_found": len(trends_found),
            "trends": trends_found
        }
    
    def _search_trend(self, keyword: str) -> dict:
        """Search for a specific trend using Tavily API"""
        try:
            # Using Anthropic's web search capability through Tavily
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": keyword,
                    "topic": "news",
                    "days": 7,
                    "max_results": 5
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                result_count = len(data.get("results", []))
                
                if result_count > 0:
                    return {
                        "keyword": keyword,
                        "mention_count": result_count,
                        "engagement_rate": min(100, result_count * 3),  # Estimate
                        "platform": "web",
                        "relevant": True
                    }
            return None
        except Exception as e:
            print(f"Error searching trend {keyword}: {e}")
            return None
    
    def store_trends(self, trends_data: dict):
        """Store discovered trends in database"""
        for trend in trends_data.get("trends", []):
            existing = self.db.query(Trend).filter(
                Trend.hashtag == trend["keyword"]
            ).first()
            
            if existing:
                existing.mention_count = trend["mention_count"]
                existing.engagement_rate = trend["engagement_rate"]
                existing.last_checked = datetime.utcnow()
                existing.relevance_to_mo = True
            else:
                new_trend = Trend(
                    hashtag=trend["keyword"],
                    keyword=trend["keyword"],
                    platform=trend.get("platform", "web"),
                    trend_category="jewelry",
                    mention_count=trend["mention_count"],
                    engagement_rate=trend.get("engagement_rate", 0),
                    relevance_to_mo=True,
                    recommended_action=f"Consider creating content around {trend['keyword']}",
                    last_checked=datetime.utcnow()
                )
                self.db.add(new_trend)
        
        self.db.commit()
        print(f"Stored {len(trends_data.get('trends', []))} trends")
    
    def generate_content_ideas(self):
        """Generate content ideas from trending topics"""
        recent_trends = self.db.query(Trend).filter(
            Trend.relevance_to_mo == True,
            Trend.last_checked >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(Trend.engagement_rate.desc()).limit(5).all()
        
        for trend in recent_trends:
            # Check if we already have a content idea for this
            existing_idea = self.db.query(ContentIdea).filter(
                ContentIdea.idea_title.contains(trend.keyword)
            ).first()
            
            if not existing_idea:
                idea = ContentIdea(
                    source_type="trend_spike",
                    idea_title=f"Create {trend.keyword} content",
                    description=f"{trend.keyword} is hot right now ({trend.mention_count} mentions). This is the time to post.",
                    design_to_feature=self._suggest_design(trend.keyword),
                    priority_score=int(trend.engagement_rate),
                    status="pending"
                )
                self.db.add(idea)
        
        self.db.commit()
    
    def _suggest_design(self, keyword: str) -> str:
        """Suggest which design to feature based on trend keyword"""
        suggestions = {
            "hip hop": "burst diamond, gold chains",
            "engagement": "custom setting, solitaire",
            "trending": "latest collection pieces",
            "viral": "bestselling designs"
        }
        
        for key, value in suggestions.items():
            if key.lower() in keyword.lower():
                return value
        
        return "new collection pieces"
    
    def run_monitoring_cycle(self):
        """Full monitoring cycle: check trends, store, generate ideas"""
        print("[TREND MONITOR] Starting cycle...")
        trends = self.check_trends()
        self.store_trends(trends)
        self.generate_content_ideas()
        print("[TREND MONITOR] Cycle complete")
        return trends
