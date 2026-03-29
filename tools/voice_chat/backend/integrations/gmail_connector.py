"""
Gmail Integration
Receives emails from Gmail inbox and posts to /message/incoming endpoint
Uses Gmail API with OAuth service account or API key
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
import base64
import re

class GmailClient:
    def __init__(self):
        self.gmail_email = os.getenv("GMAIL_ADDRESS", "")
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")  # App-specific password for IMAP
        self.gmail_api_key = os.getenv("GMAIL_API_KEY", "")  # Alternative: Gmail API key
        self.gmail_service_account_json = os.getenv("GMAIL_SERVICE_ACCOUNT_JSON", "")
        
        # Check which auth method is available
        self.use_imap = bool(self.gmail_email and self.gmail_app_password)
        self.use_api = bool(self.gmail_api_key)
        
        if not self.use_imap and not self.use_api:
            print("⚠️  Gmail not configured. Set GMAIL_ADDRESS + GMAIL_APP_PASSWORD for IMAP, or GMAIL_API_KEY for API.")
    
    def _extract_email_address(self, email_string: str) -> str:
        """Extract email address from 'Name <email@domain.com>' format"""
        match = re.search(r'<(.+?)>', email_string)
        if match:
            return match.group(1)
        return email_string.strip()
    
    def _clean_text(self, text: str) -> str:
        """Remove excessive whitespace and common email artifacts"""
        if not text:
            return ""
        # Remove unicode/html artifacts
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Collapse multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove common signatures/footers (-- separator indicates signature)
        if '\n--' in text:
            text = text.split('\n--')[0]
        return text.strip()
    
    def get_unread_messages(self, limit: int = 20) -> List[Dict]:
        """
        Fetch unread emails from Gmail inbox
        Returns list of dicts with: from, subject, message, timestamp, message_id
        """
        if not self.use_imap and not self.use_api:
            return []
        
        try:
            if self.use_imap:
                return self._get_via_imap(limit)
            else:
                return self._get_via_api(limit)
        except Exception as e:
            print(f"❌ Error fetching Gmail messages: {e}")
            return []
    
    def _get_via_imap(self, limit: int = 20) -> List[Dict]:
        """Fetch emails via IMAP (simpler, no API setup needed)"""
        import imaplib
        
        messages = []
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(self.gmail_email, self.gmail_app_password)
            mail.select("INBOX")
            
            # Search for unread emails
            status, email_ids = mail.search(None, "UNSEEN")
            
            if status == "OK":
                email_id_list = email_ids[0].split()[-limit:]  # Get last N unread
                
                for email_id in email_id_list:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    if status == "OK":
                        try:
                            import email as email_lib
                            
                            msg = email_lib.message_from_bytes(msg_data[0][1])
                            
                            from_addr = self._extract_email_address(msg.get("From", "unknown@gmail.com"))
                            subject = msg.get("Subject", "(no subject)")
                            timestamp_str = msg.get("Date", "")
                            
                            # Parse email body
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        try:
                                            body = part.get_payload(decode=True).decode("utf-8")
                                            break
                                        except:
                                            pass
                            else:
                                try:
                                    body = msg.get_payload(decode=True).decode("utf-8")
                                except:
                                    body = msg.get_payload()
                            
                            body = self._clean_text(body)
                            
                            # Combine subject + body for message_text
                            message_text = f"{subject}\n\n{body}" if body else subject
                            
                            messages.append({
                                "from": from_addr,
                                "customer_name": from_addr.split("@")[0],  # Use email prefix as name
                                "message": message_text,
                                "subject": subject,
                                "timestamp": timestamp_str,
                                "message_id": email_id.decode() if isinstance(email_id, bytes) else email_id
                            })
                        except Exception as e:
                            print(f"  Warning parsing email {email_id}: {e}")
                            continue
            
            mail.close()
            mail.logout()
        
        except imaplib.IMAP4.error as e:
            print(f"❌ IMAP error: {e}")
        
        return messages
    
    def _get_via_api(self, limit: int = 20) -> List[Dict]:
        """Fetch emails via Gmail API (requires API key or service account setup)"""
        # This is a placeholder for API-based fetching
        # Requires: google-auth-oauthlib, google-auth-httplib2, google-api-python-client
        print("⚠️  Gmail API fetching not yet implemented. Use IMAP method instead.")
        return []
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read (for IMAP)"""
        if not self.use_imap:
            return False
        
        try:
            import imaplib
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(self.gmail_email, self.gmail_app_password)
            mail.select("INBOX")
            mail.store(message_id, "+FLAGS", "\\Seen")
            mail.close()
            mail.logout()
            return True
        except Exception as e:
            print(f"Error marking email as read: {e}")
            return False
    
    def ingest_to_backend(self, backend_url: str = "http://127.0.0.1:8011") -> Dict:
        """
        Fetch unread Gmail messages and post them to the backend
        Returns count of messages ingested
        """
        messages = self.get_unread_messages(limit=20)
        
        if not messages:
            return {"status": "ok", "count": 0, "message": "No unread emails"}
        
        endpoint = f"{backend_url}/message/incoming"
        ingested = 0
        errors = []
        
        for msg in messages:
            try:
                payload = {
                    "channel": "email",
                    "from": msg["from"],
                    "customer_name": msg["customer_name"],
                    "message": msg["message"],
                    "subject": msg.get("subject", ""),
                    "external_id": msg.get("message_id", "")
                }
                
                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    ingested += 1
                    # Mark as read on backend success
                    self.mark_as_read(msg.get("message_id", ""))
                    print(f"✅ Ingested email from {msg['from']}: {msg.get('subject', '(no subject)')}")
                else:
                    errors.append(f"Status {response.status_code} for {msg['from']}")
            
            except Exception as e:
                errors.append(f"Error posting {msg['from']}: {str(e)}")
        
        result = {
            "status": "ok" if not errors else "partial",
            "count": ingested,
            "total": len(messages),
            "errors": errors if errors else None
        }
        
        if errors:
            print(f"⚠️  {len(errors)} errors during ingestion: {errors}")
        
        return result


# Standalone function for scheduled jobs
def sync_gmail_to_backend(backend_url: str = "http://127.0.0.1:8011"):
    """
    Standalone function to sync Gmail in a background job
    Call this from jobs.py at regular intervals
    """
    client = GmailClient()
    result = client.ingest_to_backend(backend_url)
    return result
