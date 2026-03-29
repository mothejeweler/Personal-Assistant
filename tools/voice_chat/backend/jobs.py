"""
Background Job Scheduler
Runs monitoring jobs on a schedule:
- Trends: Every hour
- Inventory: Every 2 hours  
- DM Analysis: Every 30 minutes
- Daily standup: Every morning at 8 AM
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
import pytz

from database.models import SessionLocal
from monitors.trend_monitor import TrendMonitor
from monitors.inventory_monitor import InventoryMonitor
from monitors.dm_monitor import DMMonitor
from integrations.twilio_handler import TwilioMessenger
from integrations.gmail_connector import sync_gmail_to_backend

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.configure(timezone=pytz.UTC)

def run_trend_monitor():
    """Hourly trend monitoring"""
    try:
        db = SessionLocal()
        monitor = TrendMonitor(db)
        result = monitor.run_monitoring_cycle()
        logger.info(f"Trend monitor completed: {result}")
        db.close()
    except Exception as e:
        logger.error(f"Trend monitor error: {e}")

def run_inventory_monitor():
    """Every 2 hours inventory monitoring"""
    try:
        db = SessionLocal()
        monitor = InventoryMonitor(db)
        result = monitor.run_monitoring_cycle()
        logger.info(f"Inventory monitor completed: {result}")
        db.close()
    except Exception as e:
        logger.error(f"Inventory monitor error: {e}")

def run_dm_monitor():
    """Every 30 minutes DM analysis"""
    try:
        db = SessionLocal()
        monitor = DMMonitor(db)
        result = monitor.run_monitoring_cycle()
        logger.info(f"DM monitor completed: {result}")
        db.close()
    except Exception as e:
        logger.error(f"DM monitor error: {e}")

def check_and_resume_overrides():
    """Every 5 minutes: Check for customers whose override period has expired"""
    try:
        db = SessionLocal()
        from database.models import Customer
        from datetime import datetime
        
        # Find customers with expired overrides
        expired_overrides = db.query(Customer).filter(
            Customer.mo_override == True,
            Customer.auto_resume_at <= datetime.utcnow()
        ).all()
        
        for customer in expired_overrides:
            customer.mo_override = False
            customer.override_at = None
            customer.auto_resume_at = None
            logger.info(f"Auto-resumed Raj for customer {customer.first_name}")
        
        if expired_overrides:
            db.commit()
            logger.info(f"Auto-resumed {len(expired_overrides)} customers")
        
        db.close()
    except Exception as e:
        logger.error(f"Override check error: {e}")

def process_message_queue():
    """Every minute: Process queued messages that are ready to send"""
    try:
        db = SessionLocal()
        from database.models import MessageQueue
        from datetime import datetime
        
        # Find messages that are scheduled and ready to send
        ready_to_send = db.query(MessageQueue).filter(
            MessageQueue.status == 'queued',
            MessageQueue.scheduled_send_at <= datetime.utcnow()
        ).all()
        
        if not ready_to_send:
            db.close()
            return
        
        for queued_msg in ready_to_send:
            try:
                # Get customer data
                from database.models import Customer
                customer = db.query(Customer).filter(Customer.id == queued_msg.customer_id).first()
                
                if not customer:
                    queued_msg.status = 'failed'
                    queued_msg.error_message = 'Customer not found'
                    continue
                
                # Send through appropriate channel
                messenger = TwilioMessenger()
                
                if queued_msg.channel == 'whatsapp' and customer.phone:
                    messenger.send_whatsapp(customer.phone, queued_msg.message_text)
                    queued_msg.status = 'sent'
                    queued_msg.sent_at = datetime.utcnow()
                    logger.info(f"Sent queued WhatsApp message to {customer.first_name} (delay: {(queued_msg.sent_at - queued_msg.queued_at).seconds}s)")
                
                elif queued_msg.channel == 'sms' and customer.phone:
                    messenger.send_sms(customer.phone, queued_msg.message_text)
                    queued_msg.status = 'sent'
                    queued_msg.sent_at = datetime.utcnow()
                    logger.info(f"Sent queued SMS to {customer.first_name} (delay: {(queued_msg.sent_at - queued_msg.queued_at).seconds}s)")
                
                elif queued_msg.channel == 'instagram' and customer.instagram_username:
                    from integrations.instagram_connector import InstagramClient
                    instagram = InstagramClient()
                    instagram.send_direct_message(customer.instagram_username, queued_msg.message_text)
                    queued_msg.status = 'sent'
                    queued_msg.sent_at = datetime.utcnow()
                    logger.info(f"Sent queued Instagram DM to {customer.first_name} (delay: {(queued_msg.sent_at - queued_msg.queued_at).seconds}s)")
                
                else:
                    queued_msg.status = 'failed'
                    queued_msg.error_message = 'No valid channel or customer contact info'
                
            except Exception as e:
                queued_msg.status = 'failed'
                queued_msg.error_message = str(e)
                queued_msg.retry_count += 1
                logger.error(f"Error sending queued message {queued_msg.id}: {e}")
        
        db.commit()
        db.close()
        logger.info(f"Message queue processor: Sent {len([m for m in ready_to_send if m.status == 'sent'])} messages")
        
    except Exception as e:
        logger.error(f"Message queue processor error: {e}")

def send_morning_standup():
    """Send daily standup at 8 AM"""
    try:
        db = SessionLocal()
        from raj_core.context_engine import RajContextEngine
        
        engine = RajContextEngine(db)
        standup = engine.get_daily_standup()
        
        # Format message
        message = f"Good morning Mo! 📊 Here's your Raj briefing:\n"
        message += f"Messages: {standup.get('standup', {}).get('messages_received', 0)} in\n"
        message += f"High-intent customers: {standup.get('high_intent_customers', [])}\n"
        message += f"Trends: {len(standup.get('trends', []))} Hot topics\n"
        
        # Send to Mo via WhatsApp
        import os
        messenger = TwilioMessenger()
        mo_phone = os.getenv("MO_WHATSAPP_PHONE")
        if mo_phone:
            messenger.send_whatsapp(mo_phone, message)
        
        logger.info("Morning standup sent")
        db.close()
    except Exception as e:
        logger.error(f"Morning standup error: {e}")

def run_gmail_sync():
    """Sync unread Gmail messages every 10 minutes"""
    try:
        import os
        backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8011")
        result = sync_gmail_to_backend(backend_url)
        
        if result.get("count", 0) > 0:
            logger.info(f"✅ Gmail sync: Ingested {result['count']} emails")
        
    except Exception as e:
        logger.error(f"Gmail sync error: {e}")


def start_scheduler():
    """Start the background job scheduler"""
    
    # Trend monitoring - every hour
    scheduler.add_job(
        run_trend_monitor,
        trigger=IntervalTrigger(hours=1),
        id='trend_monitor',
        name='Hourly Trend Monitor'
    )
    
    # Inventory monitoring - every 2 hours
    scheduler.add_job(
        run_inventory_monitor,
        trigger=IntervalTrigger(hours=2),
        id='inventory_monitor',
        name='Every 2 Hours Inventory Monitor'
    )
    
    # DM analysis - every 30 minutes
    scheduler.add_job(
        run_dm_monitor,
        trigger=IntervalTrigger(minutes=30),
        id='dm_monitor',
        name='Every 30 Minutes DM Monitor'
    )
    
    # Auto-resume overrides - every 5 minutes
    scheduler.add_job(
        check_and_resume_overrides,
        trigger=IntervalTrigger(minutes=5),
        id='auto_resume',
        name='Check & Auto-Resume Overrides'
    )
    
    # Message queue processor - every minute (processes queued messages)
    scheduler.add_job(
        process_message_queue,
        trigger=IntervalTrigger(minutes=1),
        id='message_queue_processor',
        name='Process Queued Messages (1-5min delay)'
    )
    
    # Morning standup - 8 AM daily
    scheduler.add_job(
        send_morning_standup,
        trigger=CronTrigger(hour=8, minute=0),
        id='morning_standup',
        name='Daily Morning Standup at 8 AM'
    )
    
    # Gmail sync - every 10 minutes
    scheduler.add_job(
        run_gmail_sync,
        trigger=IntervalTrigger(minutes=10),
        id='gmail_sync',
        name='Gmail Inbox Sync (10min)'
    )
    
    scheduler.start()
    logger.info("🚀 Background scheduler started with 7 monitoring jobs")
    
    return scheduler

if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            input()  # Keep running
    except KeyboardInterrupt:
        scheduler.shutdown()
