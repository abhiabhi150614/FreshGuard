# FreshGuard 🥬

**Smart Food Spoilage Detection System**

Production-ready real-time food quality monitoring using MQ-135 gas sensor and ESP32 with intelligent alerts.

## ✨ Features

- 📊 **Real-time Dashboard** - Live monitoring with interactive charts
- 🚨 **Smart Alerts** - Voice calls via Twilio with spam protection
- 💾 **Data Persistence** - PostgreSQL + Redis for reliability
- 🔄 **Background Tasks** - Automated data collection and cleanup
- 🐳 **Docker Ready** - One-command deployment
- 📱 **Mobile Responsive** - Works on all devices

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ESP32 + MQ135 │────│  Streamlit App  │────│   PostgreSQL    │
│   Gas Sensor    │    │   Dashboard     │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              │                         │
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Celery Worker  │────│     Redis       │
                       │ Background Tasks│    │     Cache       │
                       └─────────────────┘    └─────────────────┘
                              │
                              │
                       ┌─────────────────┐
                       │  Twilio API     │
                       │ Voice Alerts    │
                       └─────────────────┘
```

## Quick Start

### 1. Environment Setup

```bash
git clone https://github.com/yourusername/freshguard.git
cd freshguard
cp .env.example .env
# Edit .env with your settings
```

### 2. Docker Deployment (Recommended)

```bash
docker-compose up -d
open http://localhost:8501
```

### 3. Local Development

```bash
pip install -r requirements.txt
docker-compose up -d db redis
python run.py
```

## ⚙️ Configuration

**Key Environment Variables:**

| Variable | Description | Example |
|----------|-------------|----------|
| `DEFAULT_DEVICE_URL` | ESP32 IP address | `http://192.168.1.100` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | `ACxxxxxxxx...` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | `your_token` |
| `TWILIO_PHONE_NUMBER` | Alert phone number | `+1234567890` |
| `RATIO_FRESH` | Fresh threshold | `0.8` |
| `RATIO_WARNING` | Spoiled threshold | `0.5` |

**Sensor Thresholds:**
- 🟢 **Fresh**: Ratio > 0.8
- 🟡 **Warning**: 0.5 < Ratio ≤ 0.8  
- 🔴 **Spoiled**: Ratio ≤ 0.5 (triggers alert)

## 🔌 ESP32 API

**Required Endpoints:**
- `GET /status` - Current sensor data
- `GET /calibrate` - Calibrate in fresh air

**Response Format:**
```json
{
  "device": "esp32_001",
  "Ro": 650000.0,
  "Rs": 325000.0, 
  "ratio": 0.5,
  "Vout": 2.1
}
```

## 📊 Dashboard

- **Live Metrics** - Real-time sensor data with color coding
- **Historical Charts** - Interactive time-series with thresholds
- **Smart Alerts** - Voice calls with cooldown protection
- **Data Export** - CSV download for analysis

## 🚀 Production Deployment

```bash
# Docker (Recommended)
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker=3

# Manual setup
pip install -r requirements.txt
python run.py
```

## 🔧 Monitoring

- **Health Checks** - Database, Redis, device connectivity
- **Structured Logging** - JSON format with error tracking  
- **Auto Cleanup** - 30-day data retention
- **Performance Metrics** - Built-in monitoring

## 🔍 Troubleshooting

**Common Issues:**
- **Device Connection** - Check ESP32 IP and network
- **Database Error** - Verify PostgreSQL is running
- **Twilio Alerts** - Check credentials and phone format

**Debug Mode:**
```bash
export LOG_LEVEL=DEBUG
streamlit run app.py --logger.level=debug
```

## 📚 API Reference

**Sensor Service:**
- `fetch_device_status()` - Get live data
- `save_reading()` - Store to database
- `get_readings_history()` - Historical data

**Alert Service:**
- `create_alert()` - Generate alerts
- `send_voice_alert()` - Twilio integration
- `resolve_alerts()` - Mark resolved

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Commit changes
4. Push and create PR

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ for food safety**