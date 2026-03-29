"""
Instagram Direct Messages Integration
Handles receiving and sending Instagram DMs
"""

import os
import requests
from datetime import datetime

class InstagramClient:
    def __init__(self):
        self.business_account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")  # Using Meta Graph API token
        self.api_version = "v18.0"
        self.base_url = f"https://graph.instagram.com/{self.api_version}"
    
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_direct_messages(self) -> list:
        """Get recent direct messages"""
        try:
            response = requests.get(
                f"{self.base_url}/{self.business_account_id}/conversations",
                headers=self.get_headers(),
                params={
                    "fields": "id,participants,sms_text,updated_time",
                    "limit": 25
                }
            )
            response.raise_for_status()
            conversations = response.json().get("data", [])
            
            messages = []
            for conv in conversations:
                conv_id = conv.get("id")
                # Get messages in this conversation
                msg_response = requests.get(
                    f"{self.base_url}/{conv_id}/messages",
                    headers=self.get_headers(),
                    params={"fields": "from,message,timestamp"}
                )
                
                if msg_response.status_code == 200:
                    for msg in msg_response.json().get("data", []):
                        messages.append({
                            "from": msg.get("from", {}).get("username"),
                            "message": msg.get("message"),
                            "timestamp": msg.get("timestamp"),
                            "conversation_id": conv_id
                        })
            
            return messages
        except Exception as e:
            print(f"Error fetching Instagram messages: {e}")
            return []
    
    def send_direct_message(self, recipient_id: str, message: str) -> dict:
        """Send a direct message"""
        try:
            response = requests.post(
                f"{self.base_url}/{self.business_account_id}/messages",
                headers=self.get_headers(),
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message}
                }
            )
            response.raise_for_status()
            result = response.json()
            return {
                "status": "success",
                "message_id": result.get("message_id"),
                "channel": "instagram"
            }
        except Exception as e:
            print(f"Error sending Instagram message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "channel": "instagram"
            }
    
    def get_customer_info(self, username: str) -> dict:
        """Get customer info from Instagram username"""
        try:
            response = requests.get(
                f"{self.base_url}/ig_hashtag_search",
                headers=self.get_headers(),
                params={"user_id": self.business_account_id, "search_query": username}
            )
            # This is a simplified version - real implementation would use Instagram API properly
            return {"username": username}
        except Exception as e:
            print(f"Error fetching Instagram user info: {e}")
            return {}
    
    def get_hashtag_insights(self, hashtag: str) -> dict:
        """Get insights for a hashtag (for trend monitoring)"""
        try:
            response = requests.get(
                f"{self.base_url}/ig_hashtag_search",
                headers=self.get_headers(),
                params={
                    "user_id": self.business_account_id,
                    "search_query": hashtag
                }
            )
            response.raise_for_status()
            # Would need proper hashtag insights implementation
            return {"hashtag": hashtag, "status": "searched"}
        except Exception as e:
            print(f"Error getting hashtag insights: {e}")
            return {}
