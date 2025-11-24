"""Background tasks for data collection and processing"""
from celery import Celery
from datetime import datetime, timedelta
import structlog
from services.sensor_service import SensorService
from services.alert_service import AlertService
from models import Device, SessionLocal
from config import settings

# Configure Celery
celery_app = Celery(
    'food_spoil_detector',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'collect-sensor-data': {
            'task': 'tasks.collect_all_devices_data',
            'schedule': settings.POLL_INTERVAL,
        },
        'cleanup-old-data': {
            'task': 'tasks.cleanup_old_data',
            'schedule': 3600.0,  # Every hour
        },
    }
)

logger = structlog.get_logger()

@celery_app.task
def collect_device_data(device_id: str, device_url: str):
    """Collect data from a single device"""
    sensor_service = SensorService()
    alert_service = AlertService()
    
    try:
        raw_data = sensor_service.fetch_device_status(device_url)
        normalized = sensor_service.normalize_reading(raw_data, device_id)
        reading = sensor_service.save_reading(normalized)
        
        # Check for alerts
        ratio = normalized["ratio"]
        if ratio <= settings.RATIO_WARNING:
            alert_service.create_alert(device_id, "spoiled", ratio)
        elif ratio <= settings.RATIO_FRESH:
            alert_service.create_alert(device_id, "warning", ratio)
        else:
            alert_service.resolve_alerts(device_id)
        
        logger.info("Data collected", device_id=device_id, ratio=ratio)
        return {"status": "success", "ratio": ratio}
        
    except Exception as e:
        logger.error("Data collection failed", device_id=device_id, error=str(e))
        return {"status": "error", "error": str(e)}

@celery_app.task
def collect_all_devices_data():
    """Collect data from all active devices"""
    session = SessionLocal()
    try:
        devices = session.query(Device).filter(Device.is_active == True).all()
        
        for device in devices:
            collect_device_data.delay(device.device_id, device.url)
        
        logger.info("Scheduled data collection", device_count=len(devices))
        return {"scheduled_devices": len(devices)}
        
    finally:
        session.close()

@celery_app.task
def cleanup_old_data():
    """Clean up old sensor readings and alerts"""
    session = SessionLocal()
    try:
        # Keep only last 30 days of data
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        from models import SensorReading, Alert
        
        # Delete old readings
        old_readings = session.query(SensorReading)\
            .filter(SensorReading.timestamp < cutoff_date)\
            .delete()
        
        # Delete old resolved alerts
        old_alerts = session.query(Alert)\
            .filter(
                Alert.timestamp < cutoff_date,
                Alert.is_resolved == True
            ).delete()
        
        session.commit()
        
        logger.info("Cleanup completed", 
                   readings_deleted=old_readings,
                   alerts_deleted=old_alerts)
        
        return {
            "readings_deleted": old_readings,
            "alerts_deleted": old_alerts
        }
        
    except Exception as e:
        session.rollback()
        logger.error("Cleanup failed", error=str(e))
        raise
    finally:
        session.close()

@celery_app.task
def send_daily_report(device_id: str, email: str):
    """Send daily summary report"""
    sensor_service = SensorService()
    
    try:
        # Get last 24 hours of data
        history = sensor_service.get_readings_history(device_id, hours=24)
        
        if not history:
            return {"status": "no_data"}
        
        # Calculate statistics
        ratios = [r["ratio"] for r in history]
        avg_ratio = sum(ratios) / len(ratios)
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        
        alert_count = sum(1 for r in history if r["is_alert"])
        
        report = {
            "device_id": device_id,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "readings_count": len(history),
            "avg_ratio": round(avg_ratio, 3),
            "min_ratio": round(min_ratio, 3),
            "max_ratio": round(max_ratio, 3),
            "alert_count": alert_count
        }
        
        # Here you would send the email
        # For now, just log the report
        logger.info("Daily report generated", **report)
        
        return report
        
    except Exception as e:
        logger.error("Report generation failed", device_id=device_id, error=str(e))
        return {"status": "error", "error": str(e)}