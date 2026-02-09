# 🏥 TTSH@Home Nurse Scheduling System

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ttshmic.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Automated nurse scheduling and route optimization for the Mobile Inpatient Care (MIC) at Home program.**

![Demo Screenshot](docs/screenshot.png)

## 📋 Overview

This system solves the daily challenge of scheduling nurse home visits while:
- ✅ Respecting time windows (blood draws by 10 AM, IV timings, etc.)
- ✅ Minimizing travel time (eliminating route zigzagging)
- ✅ Enforcing capacity constraints (max 6 visits per nurse)
- ✅ Maintaining continuity of care (same nurse for 8-hr IV patients)
- ✅ Considering language preferences and geographic zones

### The Problem We Solve

| Before | After |
|--------|-------|
| 30-60 min manual scheduling | < 5 min automated |
| Route zigzagging (inefficient) | Optimized geographic clustering |
| Occasional constraint violations | Zero hard constraint violations |
| Inconsistent decisions | Explainable, repeatable results |

## 🚀 Quick Start

### Option 1: Run Locally (Recommended for Testing)

```bash
# Clone the repository
git clone https://github.com/your-username/ttsh-scheduler.git
cd ttsh-scheduler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`

### Option 2: Google Colab (No Installation)

1. Open the notebook in Google Colab:
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/your-username/ttsh-scheduler/blob/main/notebooks/TTSH_Scheduler_Complete_Guide.ipynb)

2. Run all cells to learn and experiment

### Option 3: Deploy to Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your forked repository
5. Set main file path to `streamlit_app.py`
6. Click "Deploy"

Your app will be live at `https://your-app-name.streamlit.app`

## 📁 Project Structure

```
ttsh-scheduler/
├── streamlit_app.py          # Web interface (Streamlit)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── notebooks/
│   └── TTSH_Scheduler_Complete_Guide.ipynb  # Learning notebook
├── data/
│   └── sample_patient_data.xlsx             # Sample test data
├── docs/
│   ├── screenshot.png        # Demo screenshot
│   └── architecture.md       # Technical architecture
└── src/                      # (Future) Modular source code
    ├── parser.py
    ├── scheduler.py
    └── visualizer.py
```

## 📖 How It Works

### 1. Data Input
Upload an Excel file with these columns:
- `Name` - Patient name
- `Location` - Address (HDB block format supported)
- `Home Visit task/time` - Procedure type (e.g., "IV ABx 8 hrly", "Blood taking")
- `Session 2 task/time` - Second visit if needed
- `Priority` - "Priority" or "Normal"
- `Language` - Patient's preferred language

### 2. Constraint Processing
The system identifies:
- **Blood draws**: Must complete by 10:00 AM (for lab delivery by 11:00 AM)
- **8-hr IV**: Needs AM and PM visits, same nurse required
- **Priority patients**: Fixed time slots honored
- **Capacity**: Max 3 AM + 3 PM visits per nurse

### 3. Optimization
Using Google OR-Tools Vehicle Routing Problem (VRP) solver:
- Models nurses as "vehicles"
- Patients as "delivery locations"
- Minimizes total travel time
- Respects all time windows and constraints

### 4. Output
- Interactive schedule view
- Route visualization on Singapore map
- Downloadable Excel export
- Analytics dashboard

## 🔧 Configuration

Edit these settings in the code or via the UI:

| Setting | Default | Description |
|---------|---------|-------------|
| Work hours | 08:30-16:30 | Operating hours |
| Lunch window | 11:00-14:00 | 1-hour break within this window |
| Max AM visits | 3 | Per nurse |
| Max PM visits | 3 | Per nurse |
| Blood draw deadline | 10:00 | Must complete by this time |
| Default travel time | 20 min | Between zones |
| Same-zone travel | 15 min | Within same zone |

## 🗺️ Singapore Zones

Postal codes are mapped to zones for efficient clustering:

| Zone | Postal Prefixes | Example Areas |
|------|-----------------|---------------|
| North | 50-57, 72-73 | Ang Mo Kio, Yishun, Woodlands |
| South | 01-10 | Raffles, Marina, Sentosa |
| East | 38-49 | Bedok, Tampines, Pasir Ris |
| West | 60-71 | Jurong, Clementi, Bukit Batok |
| Central | 11-37 | Toa Payoh, Bishan, Novena |

## 📊 Sample Data Format

```csv
Name,Location,Home Visit task/time,Session 2 task/time,Priority,Language
Tan AH,"Blk 123 Ang Mo Kio Ave 4 S(560123)",IV ABx 8 hrly,IV ABx 8 hrly (PM),Normal,Mandarin
Lim BK,"Blk 456 Toa Payoh Lor 1 S(310456)",Blood taking,,Normal,English
Wong CL,"Blk 789 Hougang Ave 5 S(530789)",IV ABx,,Normal,English
Lee EF,"Blk 567 Woodlands Dr 14 S(730567)",Others (Priority) 10:00,,Priority,Malay
```

## 🔄 Development Roadmap

### Phase 1: MVP (Current)
- [x] Excel parsing with TTSH format
- [x] Basic constraint solver
- [x] Streamlit web interface
- [x] Schedule export

### Phase 2: Enhanced (Planned)
- [ ] Full OR-Tools VRP integration
- [ ] OneMap API geocoding
- [ ] Google Maps travel time API
- [ ] Drag-and-drop schedule adjustments

### Phase 3: Advanced (Future)
- [ ] Historical learning (visit duration predictions)
- [ ] Real-time traffic integration
- [ ] Mobile nurse interface
- [ ] Epic EMR integration

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License - feel free to use for your own healthcare scheduling projects!

## 🙏 Acknowledgments

- [Google OR-Tools](https://developers.google.com/optimization) - Optimization engine
- [Streamlit](https://streamlit.io/) - Web interface framework
- [OneMap](https://www.onemap.gov.sg/) - Singapore geocoding API
- TTSH Mobile Inpatient Care team - Domain expertise

## 📧 Contact

For questions about implementing this at your healthcare facility:
- Open an issue on GitHub
- Email: [your-email@example.com]

---

*Built with ❤️ for better healthcare delivery*
