"""Production Streamlit dashboard for food spoilage detection"""
import random
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
import altair as alt
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import structlog

from config import settings
from models import create_tables
from services.sensor_service import SensorService
from services.alert_service import AlertService

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize database
create_tables()

# Page config
st.set_page_config(
    page_title="Food Spoilage Monitor",
    page_icon="🥬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def get_services():
    return SensorService(), AlertService()

sensor_service, alert_service = get_services()

def get_mock_reading() -> Dict[str, Any]:
    """Generate mock sensor reading for testing"""
    mock_ro = st.session_state.get("mock_ro", random.uniform(200000, 700000))
    st.session_state["mock_ro"] = mock_ro
    
    return {
        "device": "mock_esp32",
        "Ro": round(mock_ro, 2),
        "Rs": round(mock_ro * random.uniform(0.3, 1.5), 1),
        "Vout": round(random.uniform(0.05, 3.5), 3),
        "status": "mock"
    }

def process_reading(raw_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
    """Process and save sensor reading"""
    try:
        normalized = sensor_service.normalize_reading(raw_data, device_id)
        reading = sensor_service.save_reading(normalized)
        
        # Check for alerts
        ratio = normalized["ratio"]
        if ratio <= settings.RATIO_WARNING:
            alert_type = "spoiled"
            phone = st.session_state.get("alert_phone")
            if phone and alert_service.should_send_alert(device_id, alert_type):
                alert_service.create_alert(device_id, alert_type, ratio, phone)
        elif ratio <= settings.RATIO_FRESH:
            alert_type = "warning"
            alert_service.create_alert(device_id, alert_type, ratio)
        else:
            # Resolve alerts when fresh
            alert_service.resolve_alerts(device_id)
        
        return normalized
        
    except Exception as e:
        logger.error("Processing failed", error=str(e))
        raise

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    device_url = st.text_input(
        "Device URL",
        value=st.session_state.get("device_url", settings.DEFAULT_DEVICE_URL),
        help="ESP32 device base URL"
    )
    
    device_id = st.text_input(
        "Device ID",
        value=st.session_state.get("device_id", "esp32_001"),
        help="Unique device identifier"
    )
    
    poll_interval = st.slider(
        "Poll Interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.get("poll_interval", settings.POLL_INTERVAL)
    )
    
    st.subheader("🚨 Alert Settings")
    
    alert_phone = st.text_input(
        "Alert Phone Number",
        value=st.session_state.get("alert_phone", ""),
        help="Phone number for voice alerts (e.g., +1234567890)"
    )
    
    ratio_fresh = st.number_input(
        "Fresh Threshold",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.get("ratio_fresh", settings.RATIO_FRESH),
        step=0.1,
        format="%.2f"
    )
    
    ratio_warning = st.number_input(
        "Warning Threshold",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.get("ratio_warning", settings.RATIO_WARNING),
        step=0.1,
        format="%.2f"
    )
    
    mock_mode = st.checkbox(
        "Mock Mode",
        value=st.session_state.get("mock_mode", False),
        help="Use simulated data for testing"
    )

# Persist settings
for key, value in {
    "device_url": device_url,
    "device_id": device_id,
    "poll_interval": poll_interval,
    "alert_phone": alert_phone,
    "ratio_fresh": ratio_fresh,
    "ratio_warning": ratio_warning,
    "mock_mode": mock_mode
}.items():
    st.session_state[key] = value

# Main title
st.title("🥬 Food Spoilage Detection System")
st.markdown("Real-time monitoring with MQ-135 gas sensor")

# Auto-refresh
count = st_autorefresh(
    interval=poll_interval * 1000,
    limit=None,
    key="auto_refresh"
)

# Fetch and process data
error_msg = None
try:
    if mock_mode:
        raw_data = get_mock_reading()
    else:
        raw_data = sensor_service.fetch_device_status(device_url)
    
    current_reading = process_reading(raw_data, device_id)
    
except Exception as e:
    error_msg = str(e)
    current_reading = sensor_service.get_latest_reading(device_id)

# Display current status
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Current Status")
    
    if error_msg:
        st.error(f"Connection Error: {error_msg}")
    
    if current_reading:
        ratio = current_reading["ratio"]
        
        # Status badge
        if ratio <= ratio_warning:
            st.error("🚨 SPOILED")
            status_color = "red"
        elif ratio <= ratio_fresh:
            st.warning("⚠️ WARNING")
            status_color = "orange"
        else:
            st.success("✅ FRESH")
            status_color = "green"
        
        # Metrics
        st.metric("Ratio (Rs/Ro)", f"{ratio:.3f}")
        st.metric("Rs (Ω)", f"{current_reading['rs']:,.1f}")
        st.metric("Ro (Ω)", f"{current_reading['ro']:,.1f}")
        st.metric("Voltage (V)", f"{current_reading['vout']:.3f}")
        
        # Last update
        if isinstance(current_reading['timestamp'], str):
            timestamp = current_reading['timestamp']
        else:
            timestamp = current_reading['timestamp'].strftime("%H:%M:%S")
        st.caption(f"Last update: {timestamp}")
    
    else:
        st.info("No data available")

with col2:
    st.subheader("📈 Historical Data")
    
    # Get historical data
    history = sensor_service.get_readings_history(device_id, hours=24, limit=500)
    
    if history:
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create charts
        base = alt.Chart(df).add_selection(
            alt.selection_interval(bind='scales')
        )
        
        # Ratio chart with thresholds
        ratio_chart = base.mark_line(point=True).encode(
            x=alt.X('timestamp:T', title='Time'),
            y=alt.Y('ratio:Q', title='Ratio (Rs/Ro)'),
            color=alt.condition(
                alt.datum.ratio <= ratio_warning,
                alt.value('red'),
                alt.condition(
                    alt.datum.ratio <= ratio_fresh,
                    alt.value('orange'),
                    alt.value('green')
                )
            ),
            tooltip=['timestamp:T', 'ratio:Q', 'rs:Q', 'ro:Q']
        ).properties(height=200)
        
        # Add threshold lines
        warning_line = alt.Chart(pd.DataFrame({'y': [ratio_warning]})).mark_rule(
            color='orange', strokeDash=[5, 5]
        ).encode(y='y:Q')
        
        fresh_line = alt.Chart(pd.DataFrame({'y': [ratio_fresh]})).mark_rule(
            color='green', strokeDash=[5, 5]
        ).encode(y='y:Q')
        
        ratio_with_thresholds = (ratio_chart + warning_line + fresh_line).resolve_scale(
            y='independent'
        )
        
        st.altair_chart(ratio_with_thresholds, use_container_width=True)
        
        # Voltage chart
        voltage_chart = base.mark_line().encode(
            x=alt.X('timestamp:T', title='Time'),
            y=alt.Y('vout:Q', title='Voltage (V)'),
            tooltip=['timestamp:T', 'vout:Q']
        ).properties(height=150)
        
        st.altair_chart(voltage_chart, use_container_width=True)
        
        # Recent readings table
        st.subheader("Recent Readings")
        display_df = df[['timestamp', 'ratio', 'rs', 'ro', 'vout', 'is_alert']].head(10)
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
        st.dataframe(display_df, use_container_width=True)
        
        # Export data
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"spoilage_data_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    else:
        st.info("No historical data available")

# Control buttons
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Fetch Now"):
        st.rerun()

with col2:
    if st.button("🎯 Calibrate Device") and not mock_mode:
        try:
            with st.spinner("Calibrating..."):
                result = sensor_service.calibrate_device(device_url, device_id)
            st.success(f"Calibrated! Ro = {result.get('Ro', 'N/A')}")
        except Exception as e:
            st.error(f"Calibration failed: {e}")

with col3:
    if st.button("🗑️ Clear History"):
        # This would require a method to clear history
        st.info("History cleared from display")

# Footer
st.markdown("---")
st.caption(f"Auto-refreshing every {poll_interval}s | Device: {device_id}")

if mock_mode:
    st.info("🧪 Running in mock mode - using simulated data")