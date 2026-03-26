"""
Raj's message handler - processes incoming messages and generates responses
Implements delayed response queue to make Raj seem human-like (not instant)
"""

import os
import random
from anthropic import Anthropic
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from raj_core.context_engine import RajContextEngine
from raj_core.personality import get_system_prompt
from database.models import Conversation, Customer, FirstContactRequest, MessageQueue
from integrations.twilio_handler import TwilioMessenger
from datetime import datetime, timedelta

client = Anthropic()
ANTHROPIC_RESPONSE_MODEL = os.getenv("ANTHROPIC_RESPONSE_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest"))

class RajMessageHandler:
    def __init__(self, db: Session):
        self.db = db
        self.context_engine = RajContextEngine(db)
        self.twilio = TwilioMessenger()
        self.conversation_history = []
    
    def _detect_urgency(self, customer: Customer, channel: str) -> dict:
        """
        Detect if customer is double/triple texting (urgency signal)
        
        Returns:
        {
            "is_urgent": bool,
            "consecutive_count": int,
            "time_since_last": timedelta or None
        }
        """
        # Get last 3 messages from this customer on this channel
        recent_messages = self.db.query(Conversation).filter(
            Conversation.customer_id == customer.id,
            Conversation.channel == channel,
            Conversation.direction == 'inbound'
        ).order_by(desc(Conversation.created_at)).limit(3).all()
        
        if not recent_messages:
            return {
                "is_urgent": False,
                "consecutive_count": 1,
                "time_since_last": None
            }
        
        # Check if messages are close together (within 2 minutes = double/triple text)
        now = datetime.utcnow()
        consecutive_count = 1
        
        for i, msg in enumerate(recent_messages[:-1]):  # All but oldest
            time_diff = now - msg.created_at
            
            # If message is within 2 minutes, it's consecutive
            if time_diff < timedelta(minutes=2):
                consecutive_count += 1
            else:
                break
        
        is_urgent = consecutive_count >= 2  # Double text or more = urgent
        
        time_since_last = now - recent_messages[0].created_at if recent_messages else None
        
        return {
            "is_urgent": is_urgent,
            "consecutive_count": consecutive_count,
            "time_since_last": time_since_last
        }
    
    def _calculate_send_delay(self, is_urgent: bool) -> datetime:
        """
        Calculate when to send the message
        
        If urgent (double/triple text): send immediately (0 delay)
        If normal: random 1-5 minute delay
        """
        if is_urgent:
            # Send immediately for urgent
            return datetime.utcnow()
        else:
            # Random 1-5 minute delay for normal messages
            delay_seconds = random.randint(60, 300)  # 1-5 minutes
            return datetime.utcnow() + timedelta(seconds=delay_seconds)
    
    def _queue_message(self, customer_id: int, channel: str, message: str, 
                      is_urgent: bool, consecutive_count: int) -> MessageQueue:
        """
        Queue a message for delayed sending
        """
        scheduled_send_at = self._calculate_send_delay(is_urgent)
        
        queued_msg = MessageQueue(
            customer_id=customer_id,
            channel=channel,
            message_text=message,
            status='queued',
            scheduled_send_at=scheduled_send_at,
            is_urgent=is_urgent,
            consecutive_message_count=consecutive_count,
            last_customer_message_at=datetime.utcnow()
        )
        
        self.db.add(queued_msg)
        self.db.commit()
        
        return queued_msg

    
    def _should_ask_first_contact(self, customer: Customer, channel: str, 
                                  is_general_tab: bool = False) -> bool:
        """
        Determine if this message requires first-contact confirmation
        """
        personal_channels = ['instagram', 'tiktok', 'messenger']
        
        # Don't ask if not a personal channel
        if channel not in personal_channels:
            return False
        
        # Don't ask if this is Instagram General tab (business tab)
        if channel == 'instagram' and is_general_tab:
            return False
        
        # Don't ask if customer marked as personal but raj_can_respond = False
        if customer.is_personal and not customer.raj_can_respond:
            return False
        
        # Don't ask if Mo currently has override (within 24h)
        if customer.mo_override and customer.override_at:
            resume_time = customer.override_at + timedelta(hours=24)
            if datetime.utcnow() < resume_time:
                return False
        
        # Check if customer is flagged for first contact
        return customer.first_contact_flagged or customer.is_personal
    
    def _check_mo_override(self, message: str, channel: str, 
                          customer_id: int, mo_phone: str = None) -> bool:
        """
        Detect if this message is Mo taking over (Mo replying to customer)
        Returns True if this looks like Mo's override
        """
        # If message marked as from Mo's phone number, it's an override
        if mo_phone and channel in ['whatsapp', 'sms', 'web']:
            return True
        
        return False
    
    def process_incoming_message(self, message: str, channel: str, 
                                 customer_identifier: str, 
                                 customer_name: str = None,
                                 is_general_tab: bool = False,
                                 mo_phone: str = None) -> dict:
        """
        Process an incoming message from any channel and generate Raj's response
        
        Args:
            message: The incoming message text
            channel: 'whatsapp', 'sms', 'instagram', 'tiktok', 'messenger', 'facebook', 'web'
            customer_identifier: Phone, Instagram handle, etc.
            customer_name: Customer's name
            is_general_tab: For Instagram, whether this is General tab (business) vs DM (personal)
            mo_phone: If provided and matches, indicates Mo is overriding
        """
        
        # Get or create customer
        if channel == "whatsapp" or channel == "sms":
            customer = self.context_engine.create_or_update_customer(
                phone=customer_identifier,
                first_name=customer_name
            )
        elif channel == "instagram":
            customer = self.context_engine.create_or_update_customer(
                instagram=customer_identifier,
                first_name=customer_name
            )
        elif channel == "tiktok":
            customer = self.context_engine.create_or_update_customer(
                tiktok_handle=customer_identifier,
                first_name=customer_name
            )
        else:
            customer = self.context_engine.create_or_update_customer(
                first_name=customer_name
            )
        
        # Check if Mo is overriding (taking over the conversation)
        if self._check_mo_override(message, channel, customer.id, mo_phone):
            customer.mo_override = True
            customer.override_at = datetime.utcnow()
            customer.auto_resume_at = datetime.utcnow() + timedelta(hours=24)
            self.db.commit()
            
            return {
                "status": "mo_override",
                "customer_id": customer.id,
                "response": None,
                "channel": channel,
                "note": "Mo is now handling this conversation. Raj will resume in 24 hours."
            }
        
        # Check if we should ask for first-contact approval
        if self._should_ask_first_contact(customer, channel, is_general_tab):
            # Create first contact request if one doesn't exist
            existing_request = self.db.query(FirstContactRequest).filter(
                and_(
                    FirstContactRequest.customer_id == customer.id,
                    FirstContactRequest.status == 'pending'
                )
            ).first()
            
            if not existing_request:
                first_contact_req = FirstContactRequest(
                    customer_id=customer.id,
                    channel=channel,
                    message_preview=message[:100]  # Store preview of first message
                )
                self.db.add(first_contact_req)
                self.db.commit()
            
            # Send WhatsApp to Mo asking for approval
            try:
                mo_whatsapp = os.getenv('MO_WHATSAPP_PHONE', '+1234567890')  # Should be configured
                approval_url = f"TBD_dashboard_url/approve/{customer.id}"
                
                whatsapp_msg = f"""
New customer {customer.first_name or 'Unknown'} on {channel}:

"{message}"

Should Raj respond? Reply here or check dashboard: {approval_url}
"""
                self.twilio.send_whatsapp(mo_whatsapp, whatsapp_msg.strip())
                
                # Log that reminder was sent
                if existing_request is None:
                    first_contact_req.reminder_sent_at = datetime.utcnow()
                    self.db.commit()
            except Exception as e:
                print(f"Error sending WhatsApp reminder to Mo: {e}")
            
            return {
                "status": "awaiting_approval",
                "customer_id": customer.id,
                "response": None,
                "channel": channel,
                "note": f"Waiting for Mo to approve responding to {customer.first_name}"
            }
        
        # Log incoming message
        self.context_engine.log_conversation(
            customer_id=customer.id,
            channel=channel,
            message=message,
            direction="inbound",
            response_by='raj'
        )
        
        # Detect urgency (double/triple text = urgent)
        urgency = self._detect_urgency(customer, channel)
        
        # Get customer context
        customer_data = self.context_engine.get_customer_by_phone(customer.phone) if customer.phone else None
        
        # Build enhanced system prompt with context
        extra_context = self.context_engine.build_full_context(
            customer_data=customer_data,
            include_trends=True
        )
        system_prompt = get_system_prompt(with_context=extra_context)
        
        # Call Claude to generate response
        response = self._call_claude(message, system_prompt, customer_data)
        
        # Log outgoing response
        self.context_engine.log_conversation(
            customer_id=customer.id,
            channel=channel,
            message=response,
            direction="outbound",
            response_by='raj'
        )
        
        # Queue message for delayed sending (unless urgent)
        queued_msg = self._queue_message(
            customer_id=customer.id,
            channel=channel,
            message=response,
            is_urgent=urgency['is_urgent'],
            consecutive_count=urgency['consecutive_count']
        )
        
        # Update customer last contacted
        customer.last_contacted_at = datetime.utcnow()
        self.db.commit()
        
        # Calculate actual delay
        if urgency['is_urgent']:
            delay_info = "Sent immediately (urgent: double/triple text)"
        else:
            delay_seconds = (queued_msg.scheduled_send_at - datetime.utcnow()).total_seconds()
            delay_info = f"Queued with {int(delay_seconds)}s delay (human-like response time)"
        
        return {
            "status": "success",
            "customer_id": customer.id,
            "response": response,
            "channel": channel,
            "queued_message_id": queued_msg.id,
            "urgency": urgency['is_urgent'],
            "consecutive_count": urgency['consecutive_count'],
            "delay_info": delay_info
        }
    
    def approve_first_contact(self, first_contact_id: int, approval: str) -> dict:
        """
        Mo approves or rejects a first contact request
        
        Args:
            first_contact_id: ID of the FirstContactRequest
            approval: 'raj' to let Raj respond, 'mo' to let Mo respond, or 'reject' to skip
        """
        first_contact_req = self.db.query(FirstContactRequest).filter(
            FirstContactRequest.id == first_contact_id
        ).first()
        
        if not first_contact_req:
            return {"status": "error", "message": "First contact request not found"}
        
        first_contact_req.status = 'approved' if approval in ['raj', 'mo'] else 'rejected'
        first_contact_req.mo_decision = approval
        first_contact_req.mo_decision_at = datetime.utcnow()
        
        # If approved, mark customer for auto-response in future
        if approval == 'raj':
            customer = first_contact_req.customer
            customer.first_contact_flagged = False  # No longer needs approval
            customer.raj_can_respond = True  # Allow Raj to respond
        
        self.db.commit()
        
        return {
            "status": "success",
            "first_contact_id": first_contact_id,
            "decision": approval,
            "customer_id": first_contact_req.customer_id
        }
    
    def _call_claude(self, user_message: str, system_prompt: str, customer_data: dict = None) -> str:
        """
        Call Claude API with context-aware system prompt
        SAFETY: Response is sanitized to ensure Raj is never revealed
        """
        try:
            # Build conversation with proper instructions
            messages = [
                {"role": "user", "content": user_message}
            ]
            
            response = client.messages.create(
                model=ANTHROPIC_RESPONSE_MODEL,
                max_tokens=500,
                system=system_prompt,
                messages=messages
            )
            
            generated_response = response.content[0].text
            
            # SAFETY CHECK: Ensure we never reveal Raj to the customer
            return self._sanitize_response(generated_response)
        
        except Exception as e:
            print(f"Error calling Claude: {e}")
            return "Hey, let me think on that and get back to you real quick."
    
    def _sanitize_response(self, response: str) -> str:
        """
        Safety check: Ensure response never reveals Raj or bot status to customer
        """
        # Dangerous phrases we absolutely cannot allow
        forbidden_phrases = [
            "i'm raj",
            "this is raj",
            "i'm an ai",
            "i'm a bot",
            "i'm automated",
            "mo's assistant",
            "mo's bot",
            "the team is",
            "my team is",
            "our assistant",
            "our bot",
            "our system",
            "automated response",
            "ai-generated",
            "machine learning"
        ]
        
        # Check for forbidden phrases (case-insensitive)
        response_lower = response.lower()
        for phrase in forbidden_phrases:
            if phrase in response_lower:
                # If we detect a forbidden phrase, fall back to generic but safe response
                print(f"⚠️  SAFETY: Detected forbidden phrase '{phrase}' in response - using fallback")
                return "Hey what's up, just got your message. Let me get back to you in a sec."
        
        return response
    
    def get_conversation_history(self, customer_id: int, limit: int = 20) -> list:
        """Get conversation history for a customer"""
        conversations = self.db.query(Conversation).filter(
            Conversation.customer_id == customer_id
        ).order_by(Conversation.created_at.desc()).limit(limit).all()
        
        return [
            {
                "date": c.created_at.isoformat(),
                "direction": c.direction,
                "channel": c.channel,
                "message": c.message_text
            } for c in reversed(conversations)
        ]
