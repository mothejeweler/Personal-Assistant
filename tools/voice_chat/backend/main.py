"""
Raj Backend - FastAPI Server
Main entry point for all Raj operations

Endpoints:
- POST /message/incoming - Receive messages from any channel
- POST /message/send - Send messages to customers
- GET /customer/{id} - Get customer context
- GET /status/standup - Get daily briefing
- GET /trends/current - Get current trends
- GET /inventory/status - Get inventory status
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
from datetime import datetime
from collections import defaultdict

# Load environment variables
load_dotenv()

# Import our modules
from database.models import init_db, get_db
from raj_core.context_engine import RajContextEngine
from raj_core.message_handler import RajMessageHandler
from integrations.twilio_handler import TwilioMessenger
from integrations.instagram_connector import InstagramClient
from integrations.shopify_sync import ShopifyClient
from monitors.trend_monitor import TrendMonitor
from monitors.inventory_monitor import InventoryMonitor
from monitors.dm_monitor import DMMonitor
from dashboard_ui import render_dashboard_html


PRIORITY_INTENTS = {"purchase", "custom_design", "complaint", "urgent"}
SPECIAL_REQUEST_INTENTS = {"custom_design", "quote_request", "bulk_order"}
SPECIAL_REQUEST_KEYWORDS = (
    "custom",
    "engrave",
    "resize",
    "rush",
    "urgent",
    "special",
    "wedding",
    "proposal",
    "anniversary",
    "wholesale",
)


def _normalize_channel(channel: str) -> str:
    value = (channel or "").strip().lower()
    if value in {"web", "website", "site", "contact_form"}:
        return "website"
    if value in {"insta"}:
        return "instagram"
    return value or "unknown"


def _is_special_request(intent: str, message_text: str) -> bool:
    if (intent or "").lower() in SPECIAL_REQUEST_INTENTS:
        return True
    msg = (message_text or "").lower()
    return any(keyword in msg for keyword in SPECIAL_REQUEST_KEYWORDS)


def _build_priority(conv, customer) -> tuple[str, int]:
    score = 0
    intent = (conv.parsed_intent or "").lower()

    if intent in PRIORITY_INTENTS:
        score += 2
    if (conv.sentiment or "").lower() == "negative":
        score += 2
    if conv.direction == "inbound" and not conv.responded:
        score += 2
    if getattr(customer, "is_high_value", False):
        score += 1
    if (getattr(customer, "lead_score", 0) or 0) >= 70:
        score += 1

    if score >= 5:
        return "high", score
    if score >= 3:
        return "medium", score
    return "low", score


def _serialize_conversation(conv, customer) -> dict:
    channel = _normalize_channel(conv.channel)
    special_request = _is_special_request(conv.parsed_intent, conv.message_text)
    priority_level, priority_score = _build_priority(conv, customer)
    unread = conv.direction == "inbound" and not conv.responded

    return {
        "id": conv.id,
        "channel": channel,
        "customer_id": conv.customer_id,
        "customer_name": (customer.first_name if customer and customer.first_name else "Unknown"),
        "preview": conv.message_text[:180] + "..." if len(conv.message_text or "") > 180 else (conv.message_text or ""),
        "direction": conv.direction,
        "intent": conv.parsed_intent,
        "sentiment": conv.sentiment,
        "responded": conv.responded,
        "response_by": conv.response_by,
        "mo_override": getattr(customer, "mo_override", False),
        "is_high_value": getattr(customer, "is_high_value", False),
        "lead_score": getattr(customer, "lead_score", 0),
        "unread": unread,
        "special_request": special_request,
        "priority": priority_level,
        "priority_score": priority_score,
        "timestamp": conv.created_at.isoformat(),
    }

# Initialize FastAPI app
app = FastAPI(title="Raj Backend", version="1.0.0")

# Initialize database
@app.on_event("startup")
async def startup_event():
    print("🚀 Raj Backend starting...")
    init_db()
    print("✅ Database initialized")

# ─── MESSAGE HANDLING ───

@app.post("/message/incoming")
async def handle_incoming_message(request: Request, db: Session = Depends(get_db)):
    """
    Receive incoming message from WhatsApp, Instagram, SMS, or web
    
    Expected payload:
    {
        "channel": "whatsapp" | "instagram" | "tiktok" | "email" | "sms" | "web" | "website",
        "from": "phone_number" | "instagram_username" | "email_address" | "tiktok_handle",
        "message": "message text",
        "customer_name": "optional name"
    }
    """
    try:
        data = await request.json()
        
        channel = data.get("channel", "web")
        from_id = data.get("from")
        message = data.get("message")
        customer_name = data.get("customer_name")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message required")
        
        # Process message through Raj
        handler = RajMessageHandler(db)
        response = handler.process_incoming_message(
            message=message,
            channel=channel,
            customer_identifier=from_id,
            customer_name=customer_name
        )
        
        # Send response back through appropriate channel
        await send_response_to_channel(response, from_id, channel, db)
        
        return {
            "status": "success",
            "response": response.get("response"),
            "channel": channel
        }
    
    except Exception as e:
        print(f"Error handling incoming message: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/message/send")
async def send_message(request: Request, db: Session = Depends(get_db)):
    """
    Send a message to a customer through specified channel
    
    Payload:
    {
        "customer_id": int,
        "message": "message text",
        "channel": "whatsapp" | "instagram" | "sms"
    }
    """
    try:
        data = await request.json()
        
        customer_id = data.get("customer_id")
        message = data.get("message")
        channel = data.get("channel", "whatsapp")
        
        from database.models import Customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Send via appropriate channel
        if channel == "whatsapp" and customer.phone:
            messenger = TwilioMessenger()
            result = messenger.send_whatsapp(customer.phone, message)
        elif channel == "instagram" and customer.instagram_username:
            instagram = InstagramClient()
            result = instagram.send_direct_message(customer.instagram_username, message)
        elif channel == "sms" and customer.phone:
            messenger = TwilioMessenger()
            result = messenger.send_sms(customer.phone, message)
        else:
            raise HTTPException(status_code=400, detail="Invalid channel or customer info")
        
        return result
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

async def send_response_to_channel(response: dict, to_id: str, channel: str, db: Session):
    """Send Raj's response through the appropriate channel"""
    try:
        message = response.get("response")
        
        if channel == "whatsapp" and to_id:
            messenger = TwilioMessenger()
            messenger.send_whatsapp(to_id, message)
        elif channel == "instagram" and to_id:
            instagram = InstagramClient()
            instagram.send_direct_message(to_id, message)
        elif channel == "sms" and to_id:
            messenger = TwilioMessenger()
            messenger.send_sms(to_id, message)
        # For web, response is shown in API response
    except Exception as e:
        print(f"Error sending response through {channel}: {e}")

# ─── CONTEXT & INTELLIGENCE ───

@app.get("/customer/{customer_id}")
async def get_customer_context(customer_id: int, db: Session = Depends(get_db)):
    """Get full customer context"""
    try:
        engine = RajContextEngine(db)
        
        from database.models import Customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        customer_data = engine.get_customer_by_phone(customer.phone) if customer.phone else None
        
        return {
            "customer": customer_data,
            "context": engine.build_full_context(customer_data=customer_data)
        }
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/status/standup")
async def get_daily_standup(db: Session = Depends(get_db)):
    """Get Mo's daily standup briefing"""
    try:
        engine = RajContextEngine(db)
        return {
            "standup": engine.get_daily_standup(),
            "high_intent_customers": engine.get_high_intent_customers(),
            "inventory_status": engine.get_inventory_status(),
            "trends": engine.get_trending_now(),
            "content_ideas": engine.get_content_roadmap()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/trends/current")
async def get_current_trends(db: Session = Depends(get_db)):
    """Get current trending topics"""
    try:
        engine = RajContextEngine(db)
        return {
            "trends": engine.get_trending_now(limit=10),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/inventory/status")
async def get_inventory_status(db: Session = Depends(get_db)):
    """Get current inventory status"""
    try:
        engine = RajContextEngine(db)
        return engine.get_inventory_status()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── MONITORING JOBS (Manual triggers) ───

@app.post("/jobs/monitor/trends")
async def trigger_trend_monitoring(db: Session = Depends(get_db)):
    """Manually trigger trend monitoring"""
    try:
        monitor = TrendMonitor(db)
        result = monitor.run_monitoring_cycle()
        return {"status": "success", "result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/jobs/monitor/inventory")
async def trigger_inventory_monitoring(db: Session = Depends(get_db)):
    """Manually trigger inventory monitoring"""
    try:
        monitor = InventoryMonitor(db)
        result = monitor.run_monitoring_cycle()
        return {"status": "success", "result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/jobs/monitor/dms")
async def trigger_dm_monitoring(db: Session = Depends(get_db)):
    """Manually trigger DM analysis"""
    try:
        monitor = DMMonitor(db)
        result = monitor.run_monitoring_cycle()
        return {"status": "success", "result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── OVERRIDE & FIRST CONTACT APPROVAL ───

@app.post("/first-contact/approve")
async def approve_first_contact(request: Request, db: Session = Depends(get_db)):
    """
    Mo approves or rejects a first contact request
    
    Payload:
    {
        "first_contact_id": int,
        "decision": "raj" | "mo" | "reject"
    }
    """
    try:
        data = await request.json()
        first_contact_id = data.get("first_contact_id")
        decision = data.get("decision", "raj")
        
        handler = RajMessageHandler(db)
        result = handler.approve_first_contact(first_contact_id, decision)
        
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/first-contact/pending")
async def get_pending_first_contacts(db: Session = Depends(get_db)):
    """Get all pending first contact requests"""
    try:
        from database.models import FirstContactRequest, Customer
        
        pending = db.query(FirstContactRequest).filter(
            FirstContactRequest.status == 'pending'
        ).all()
        
        result = []
        for req in pending:
            customer = db.query(Customer).filter(Customer.id == req.customer_id).first()
            result.append({
                "id": req.id,
                "customer_id": req.customer_id,
                "customer_name": customer.first_name if customer else "Unknown",
                "channel": req.channel,
                "message_preview": req.message_preview,
                "created_at": req.created_at.isoformat(),
                "reminder_sent": req.reminder_sent_at is not None
            })
        
        return {"pending_requests": result, "count": len(result)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/customer/{customer_id}/override")
async def take_over_conversation(customer_id: int, db: Session = Depends(get_db)):
    """
    Mo takes over a customer conversation (Mo override)
    Raj will pause for 24 hours and resume automatically or wait for manual approval
    """
    try:
        from database.models import Customer
        from datetime import timedelta
        
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        customer.mo_override = True
        customer.override_at = datetime.utcnow()
        customer.auto_resume_at = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Raj paused for customer {customer.first_name}. Auto-resume in 24 hours.",
            "override_at": customer.override_at.isoformat(),
            "auto_resume_at": customer.auto_resume_at.isoformat()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/customer/{customer_id}/resume")
async def manually_resume_raj(customer_id: int, db: Session = Depends(get_db)):
    """
    Mo manually resumes Raj for a customer (before 24h expires)
    """
    try:
        from database.models import Customer
        
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        customer.mo_override = False
        customer.override_at = None
        customer.auto_resume_at = None
        db.commit()
        
        return {
            "status": "success",
            "message": f"Raj resumed for customer {customer.first_name}"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── UNIFIED DASHBOARD ───

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home():
    """Serve unified inbox dashboard UI."""
    return HTMLResponse(content=render_dashboard_html())

@app.get("/dashboard/messages")
async def get_unified_messages(
    filter_by: str = "all",  # 'all', 'pending', 'raj-handled', 'mo-handled'
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get unified messages across all channels for the dashboard
    
    Filter options:
    - 'all': All conversations
    - 'pending': Conversations awaiting response
    - 'raj-handled': Conversations Raj responded to
    - 'mo-handled': Conversations Mo responded to
    """
    try:
        from database.models import Conversation, Customer
        from sqlalchemy import desc
        
        query = db.query(Conversation).order_by(desc(Conversation.created_at))
        
        if filter_by == "pending":
            query = query.filter(Conversation.response_by == None)
        elif filter_by == "raj-handled":
            query = query.filter(Conversation.response_by == 'raj')
        elif filter_by == "mo-handled":
            query = query.filter(Conversation.response_by == 'mo')
        
        conversations = query.limit(limit).all()
        
        result = []
        for conv in conversations:
            customer = db.query(Customer).filter(Customer.id == conv.customer_id).first()
            result.append({
                "id": conv.id,
                "customer_id": conv.customer_id,
                "customer_name": customer.first_name if customer else "Unknown",
                "channel": conv.channel,
                "direction": conv.direction,
                "message": conv.message_text[:100] + "..." if len(conv.message_text) > 100 else conv.message_text,
                "response_by": conv.response_by or "pending",
                "mo_override": customer.mo_override if customer else False,
                "timestamp": conv.created_at.isoformat()
            })
        
        return {
            "filter": filter_by,
            "total": len(result),
            "messages": result
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/dashboard/summary")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get high-level dashboard summary"""
    try:
        from database.models import Conversation, Customer, FirstContactRequest
        from sqlalchemy import func
        
        # Count conversations by status
        total_conversations = db.query(Conversation).count()
        raj_responses = db.query(Conversation).filter(Conversation.response_by == 'raj').count()
        mo_responses = db.query(Conversation).filter(Conversation.response_by == 'mo').count()
        
        # Count customers
        total_customers = db.query(Customer).count()
        personal_customers = db.query(Customer).filter(Customer.is_personal == True).count()
        pending_override = db.query(Customer).filter(Customer.mo_override == True).count()
        
        # Count pending first contacts
        pending_first_contacts = db.query(FirstContactRequest).filter(
            FirstContactRequest.status == 'pending'
        ).count()
        
        # Messages by channel
        channels = db.query(
            Conversation.channel, 
            func.count(Conversation.id)
        ).group_by(Conversation.channel).all()
        
        return {
            "conversations": {
                "total": total_conversations,
                "raj_handled": raj_responses,
                "mo_handled": mo_responses,
                "by_channel": {ch[0]: ch[1] for ch in channels}
            },
            "customers": {
                "total": total_customers,
                "personal": personal_customers,
                "currently_overridden": pending_override
            },
            "pending": {
                "first_contacts": pending_first_contacts
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/dashboard/unified")
async def get_dashboard_unified(limit: int = 200, db: Session = Depends(get_db)):
    """
    Unified inbox payload for dashboard UI.

    Separates messages by channel and computes notifications for:
    - unread messages
    - priority conversations
    - special requests
    """
    try:
        from database.models import Conversation, Customer
        from sqlalchemy import desc

        rows = db.query(Conversation, Customer).outerjoin(
            Customer, Conversation.customer_id == Customer.id
        ).order_by(desc(Conversation.created_at)).limit(limit).all()

        channel_buckets = {
            "email": [],
            "website": [],
            "instagram": [],
            "tiktok": [],
            "other": [],
        }

        counts = defaultdict(int)
        unread_count = 0
        priority_count = 0
        special_request_count = 0

        for conv, customer in rows:
            item = _serialize_conversation(conv, customer)
            channel = item["channel"]

            if channel in channel_buckets:
                channel_buckets[channel].append(item)
            else:
                channel_buckets["other"].append(item)

            counts[channel] += 1

            if item["unread"]:
                unread_count += 1
            if item["priority"] in {"high", "medium"}:
                priority_count += 1
            if item["special_request"]:
                special_request_count += 1

        top_alerts = []
        if unread_count > 0:
            top_alerts.append(f"{unread_count} unread messages need attention")
        if priority_count > 0:
            top_alerts.append(f"{priority_count} priority conversations are active")
        if special_request_count > 0:
            top_alerts.append(f"{special_request_count} special requests detected")

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "notifications": {
                "unread": unread_count,
                "priority": priority_count,
                "special_requests": special_request_count,
                "top_alerts": top_alerts,
            },
            "counts_by_channel": dict(counts),
            "channels": channel_buckets,
            "hints": {
                "email": "Email feed appears here once channel='email' messages are ingested.",
                "tiktok": "TikTok DMs appear here once channel='tiktok' messages are ingested.",
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/dashboard/notifications")
async def get_dashboard_notifications(db: Session = Depends(get_db)):
    """Lightweight notification endpoint for unread, priority, and special requests."""
    data = await get_dashboard_unified(limit=250, db=db)
    if isinstance(data, JSONResponse):
        return data

    notifications = data.get("notifications", {})
    return {
        "generated_at": data.get("generated_at"),
        "unread": notifications.get("unread", 0),
        "priority": notifications.get("priority", 0),
        "special_requests": notifications.get("special_requests", 0),
        "top_alerts": notifications.get("top_alerts", []),
    }

# ─── HEALTH CHECK ───

@app.get("/health")
async def health_check():
    """Check if Raj backend is running"""
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
