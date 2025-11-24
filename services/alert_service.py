"""Alert and notification service"""
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional
import structlog
from twilio.rest import Client
from models import Alert, SessionLocal
from config import settings

logger = structlog.get_logger()

class AlertService:
    def __init__(self):
        self.session = SessionLocal()
        self.twilio_client = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.twilio_client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
    
    def should_send_alert(self, device_id: str, alert_type: str) -> bool:
        """Check if alert should be sent (avoid spam)"""
        cooldown_minutes = 30 if alert_type == "spoiled" else 60
        since = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        
        recent_alert = self.session.query(Alert)\
            .filter(
                Alert.device_id == device_id,
                Alert.alert_type == alert_type,
                Alert.timestamp >= since,
                Alert.is_resolved == False
            )\
            .first()
        
        return recent_alert is None
    
    def send_voice_alert(self, phone_number: str, context: str, device_id: str, ratio: float) -> Optional[str]:
        """Send voice call alert via Twilio"""
        if not self.twilio_client:
            logger.warning("Twilio not configured")
            return None
        
        try:
            encoded_context = urllib.parse.quote(context)
            webhook_url = f"{settings.WEBHOOK_URL}?context={encoded_context}"
            
            call = self.twilio_client.calls.create(
                to=phone_number,
                from_=settings.TWILIO_PHONE_NUMBER,
                url=webhook_url
            )
            
            logger.info("Voice alert sent", 
                       phone_number=phone_number,
                       call_sid=call.sid,
                       device_id=device_id)
            
            return call.sid
            
        except Exception as e:
            logger.error("Voice alert failed", 
                        phone_number=phone_number,
                        error=str(e))
            return None
    
    def create_alert(self, device_id: str, alert_type: str, ratio: float, phone_number: str = None) -> Alert:
        """Create and potentially send alert"""
        alert = Alert(
            device_id=device_id,
            alert_type=alert_type,
            ratio_value=ratio,
            phone_number=phone_number,
            timestamp=datetime.utcnow()
        )
        
        # Send voice alert if phone number provided
        if phone_number and self.should_send_alert(device_id, alert_type):
            context = f"Food spoilage alert for device {device_id}. Current ratio is {ratio:.3f}."
            call_sid = self.send_voice_alert(phone_number, context, device_id, ratio)
            alert.call_sid = call_sid
        
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)
        
        return alert
    
    def resolve_alerts(self, device_id: str, alert_type: str = None):
        """Mark alerts as resolved"""
        query = self.session.query(Alert)\
            .filter(Alert.device_id == device_id, Alert.is_resolved == False)
        
        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)
        
        alerts = query.all()
        for alert in alerts:
            alert.is_resolved = True
        
        self.session.commit()
        
        logger.info("Alerts resolved", 
                   device_id=device_id,
                   count=len(alerts))
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()