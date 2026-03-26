"""
Twilio Integration
Handles WhatsApp and SMS messaging
"""

import os
from twilio.rest import Client
from typing import dict

class TwilioMessenger:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
        self.sms_from = os.getenv("TWILIO_SMS_FROM")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_whatsapp(self, to_number: str, message: str) -> dict:
        """Send WhatsApp message"""
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.whatsapp_from,
                to=f"whatsapp:{to_number}"
            )
            return {
                "status": "success",
                "message_id": msg.sid,
                "channel": "whatsapp"
            }
        except Exception as e:
            print(f"Error sending WhatsApp: {e}")
            return {
                "status": "error",
                "error": str(e),
                "channel": "whatsapp"
            }
    
    def send_sms(self, to_number: str, message: str) -> dict:
        """Send SMS message"""
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.sms_from,
                to=to_number
            )
            return {
                "status": "success",
                "message_id": msg.sid,
                "channel": "sms"
            }
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return {
                "status": "error",
                "error": str(e),
                "channel": "sms"
            }
    
    def send_combined(self, to_number: str, message: str, 
                      prefer_whatsapp: bool = True) -> dict:
        """Send via WhatsApp if possible, fall back to SMS"""
        if prefer_whatsapp:
            result = self.send_whatsapp(to_number, message)
            if result["status"] != "success":
                result = self.send_sms(to_number, message)
        else:
            result = self.send_sms(to_number, message)
        
        return result
    
    def receive_whatsapp_webhook(self, payload: dict) -> dict:
        """Parse incoming WhatsApp webhook"""
        return {
            "from": payload.get("From", "").replace("whatsapp:", ""),
            "message": payload.get("Body", ""),
            "message_id": payload.get("MessageSid"),
            "channel": "whatsapp"
        }
    
    def receive_sms_webhook(self, payload: dict) -> dict:
        """Parse incoming SMS webhook"""
        return {
            "from": payload.get("From", ""),
            "message": payload.get("Body", ""),
            "message_id": payload.get("MessageSid"),
            "channel": "sms"
        }
