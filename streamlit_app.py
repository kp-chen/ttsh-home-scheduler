"""
TTSH@Home Nurse Scheduling System - Streamlit Web Interface
============================================================

This is the web interface for the nurse scheduling system.
Deploy on Streamlit Cloud or run locally with: streamlit run streamlit_app.py

Author: Clinical Informatics Team
Version: 1.0
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import io
import requests

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="TTSH@Home Scheduler",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# DATA STRUCTURES (Same as notebook)
# ============================================================

@dataclass
class Patient:
    """Patient information."""
    id: str
    name: str
    address: str
    postal_code: str
    zone: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    language: str = "English"

@dataclass
class Visit:
    """A scheduled visit."""
    id: str
    patient: Patient
    procedure: str
    session: str
    earliest_time: int
    latest_time: int
    duration_minutes: int = 30
    priority: int = 3
    requires_continuity: bool = False
    continuity_group: str = ""

@dataclass
class Nurse:
    """Nurse information."""
    id: str
    name: str
    languages: List[str]
    max_visits_am: int = 3
    max_visits_pm: int = 3
    preferred_zones: List[str] = None
    
    def __post_init__(self):
        if self.preferred_zones is None:
            self.preferred_zones = ["North", "South", "East", "West", "Central"]

@dataclass
class ScheduledVisit:
    """Result of scheduling."""
    visit: Visit
    nurse: Nurse
    scheduled_time: int
    travel_time_from_previous: int = 0
    sequence: int = 0


# ============================================================
# CONFIGURATION
# ============================================================

class Config:
    """System configuration constants."""
    WORK_START = 8 * 60 + 30      # 8:30 AM
    WORK_END = 16 * 60 + 30       # 4:30 PM
    LUNCH_WINDOW_START = 11 * 60  # 11:00 AM
    LUNCH_WINDOW_END = 14 * 60    # 2:00 PM
    LUNCH_DURATION = 60
    MAX_VISITS_PER_NURSE_AM = 3
    MAX_VISITS_PER_NURSE_PM = 3
    MAX_VISITS_PER_NURSE_TOTAL = 6
    DEFAULT_VISIT_DURATION = 30
    IV_VISIT_DURATION = 45
    BLOOD_DRAW_DURATION = 20
    BLOOD_LAB_DEADLINE = 11 * 60
    BLOOD_TRANSIT_TIME = 60
    BLOOD_DRAW_LATEST = BLOOD_LAB_DEADLINE - BLOOD_TRANSIT_TIME
    DEFAULT_TRAVEL_TIME = 20
    SAME_ZONE_TRAVEL_TIME = 15
    HOSPITAL_RETURN_TIME = 30
    HOSPITAL_LAT = 1.3214
    HOSPITAL_LNG = 103.8456
    
    ZONE_MAPPING = {
        "North": ["50", "51", "52", "53", "54", "55", "56", "57", "72", "73"],
        "South": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"],
        "East": ["38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49"],
        "West": ["60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71"],
        "Central": ["11", "12", "13", "14", "15", "16", "17", "18", "19", "20", 
                   "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
                   "31", "32", "33", "34", "35", "36", "37"]
    }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def minutes_to_time_string(minutes: int) -> str:
    """Convert minutes from midnight to time string."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def time_string_to_minutes(time_str: str) -> int:
    """Convert time string to minutes from midnight."""
    time_str = time_str.strip().upper()
    is_pm = "PM" in time_str
    is_am = "AM" in time_str
    time_str = time_str.replace("AM", "").replace("PM", "").strip()
    
    if ":" in time_str:
        parts = time_str.split(":")
        hours = int(parts[0])
        mins = int(parts[1]) if len(parts) > 1 else 0
    else:
        hours = int(time_str)
        mins = 0
    
    if is_pm and hours != 12:
        hours += 12
    if is_am and hours == 12:
        hours = 0
    
    return hours * 60 + mins


# ============================================================
# EXCEL PARSER
# ============================================================

class ExcelParser:
    """Parse Excel files into structured data."""
    
    PROCEDURE_TYPES = {
        "iv abx 8 hrly": {"type": "IV_8HR", "duration": 45, "needs_pair": True},
        "iv abx 12 hrly": {"type": "IV_12HR", "duration": 45, "needs_pair": True},
        "iv abx": {"type": "IV", "duration": 45, "needs_pair": False},
        "iv antibiotics": {"type": "IV", "duration": 45, "needs_pair": False},
        "blood taking": {"type": "BLOOD", "duration": 20, "needs_pair": False},
        "blood draw": {"type": "BLOOD", "duration": 20, "needs_pair": False},
        "wound dressing": {"type": "WOUND", "duration": 30, "needs_pair": False},
        "wound care": {"type": "WOUND", "duration": 30, "needs_pair": False},
        "vital signs": {"type": "VITALS", "duration": 20, "needs_pair": False},
        "others": {"type": "OTHER", "duration": 30, "needs_pair": False},
    }
    
    def __init__(self):
        self.patients = []
        self.visits = []
        self.warnings = []
    
    def parse_dataframe(self, df: pd.DataFrame) -> Tuple[List[Patient], List[Visit]]:
        """Parse DataFrame into patients and visits."""
        self.patients = []
        self.visits = []
        self.warnings = []
        
        for idx, row in df.iterrows():
            try:
                patient = self._parse_patient_row(row, idx)
                self.patients.append(patient)
                visits = self._parse_visits_for_patient(patient, row, idx)
                self.visits.extend(visits)
            except Exception as e:
                self.warnings.append(f"Row {idx}: {str(e)}")
        
        return self.patients, self.visits
    
    def _parse_patient_row(self, row: pd.Series, idx: int) -> Patient:
        """Extract patient from row."""
        name = str(row.get("Name", f"Patient_{idx}")).strip()
        address = str(row.get("Location", "")).strip()
        postal_code = self._extract_postal_code(address)
        zone = self._determine_zone(postal_code)
        language = str(row.get("Language", "English")).strip()
        if language.lower() in ["nan", "", "none"]:
            language = "English"
        
        return Patient(
            id=f"P{idx:03d}",
            name=name,
            address=address,
            postal_code=postal_code,
            zone=zone,
            language=language
        )
    
    def _extract_postal_code(self, address: str) -> str:
        """Extract postal code from address."""
        import re
        match = re.search(r'S\((\d{6})\)', address)
        if match:
            return match.group(1)
        match = re.search(r'\b(\d{6})\b', address)
        if match:
            return match.group(1)
        return "000000"
    
    def _determine_zone(self, postal_code: str) -> str:
        """Determine zone from postal code."""
        prefix = postal_code[:2]
        for zone, prefixes in Config.ZONE_MAPPING.items():
            if prefix in prefixes:
                return zone
        return "Central"
    
    def _parse_visits_for_patient(self, patient: Patient, row: pd.Series, idx: int) -> List[Visit]:
        """Create visits for a patient."""
        visits = []
        
        task1 = str(row.get("Home Visit task/time", "")).strip()
        if task1 and task1.lower() not in ["nan", "", "none"]:
            visit1 = self._create_visit(patient, task1, "AM", idx, 1)
            visits.append(visit1)
            
            proc_info = self._identify_procedure(task1)
            if proc_info.get("needs_pair", False):
                visit2 = self._create_visit(patient, task1, "PM", idx, 2)
                visit2.requires_continuity = True
                visit2.continuity_group = f"CG{idx:03d}"
                visit1.requires_continuity = True
                visit1.continuity_group = f"CG{idx:03d}"
                visits.append(visit2)
        
        task2 = str(row.get("Session 2 task/time", "")).strip()
        if task2 and task2.lower() not in ["nan", "", "none", "pm"]:
            if not any(v.session == "PM" for v in visits):
                visit2 = self._create_visit(patient, task2, "PM", idx, 2)
                visits.append(visit2)
        
        return visits
    
    def _create_visit(self, patient: Patient, task: str, session: str, 
                      patient_idx: int, visit_num: int) -> Visit:
        """Create a single visit."""
        proc_info = self._identify_procedure(task)
        earliest, latest = self._calculate_time_window(proc_info, task, session)
        
        priority = 3
        if "priority" in task.lower():
            priority = 1
        
        specific_time = self._extract_specific_time(task)
        if specific_time:
            earliest = specific_time
            latest = specific_time + 30
        
        return Visit(
            id=f"V{patient_idx:03d}_{visit_num}",
            patient=patient,
            procedure=proc_info["type"],
            session=session,
            earliest_time=earliest,
            latest_time=latest,
            duration_minutes=proc_info["duration"],
            priority=priority
        )
    
    def _identify_procedure(self, task: str) -> Dict:
        """Identify procedure type."""
        task_lower = task.lower()
        for pattern, info in self.PROCEDURE_TYPES.items():
            if pattern in task_lower:
                return info
        return {"type": "OTHER", "duration": 30, "needs_pair": False}
    
    def _calculate_time_window(self, proc_info: Dict, task: str, session: str) -> Tuple[int, int]:
        """Calculate time window for visit."""
        proc_type = proc_info["type"]
        
        if proc_type == "BLOOD":
            return (Config.WORK_START, Config.BLOOD_DRAW_LATEST)
        elif proc_type == "IV_8HR":
            if session == "AM":
                return (Config.WORK_START, 10 * 60)
            else:
                return (16 * 60, Config.WORK_END)
        elif proc_type == "IV_12HR":
            if session == "AM":
                return (Config.WORK_START, 9 * 60)
            else:
                return (Config.WORK_END - 60, Config.WORK_END)
        else:
            if session == "AM":
                return (Config.WORK_START, Config.LUNCH_WINDOW_START)
            else:
                return (Config.LUNCH_WINDOW_END, Config.WORK_END)
    
    def _extract_specific_time(self, task: str) -> Optional[int]:
        """Extract specific time from task."""
        import re
        match = re.search(r'(\d{1,2}):(\d{2})', task)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            if hours < 8:
                hours += 12
            return hours * 60 + minutes
        return None


# ============================================================
# SCHEDULER (Simplified version for Streamlit)
# ============================================================

class SimpleScheduler:
    """
    Simplified scheduler using greedy algorithm.
    For full OR-Tools version, see the notebook.
    """
    
    def __init__(self, nurses: List[Nurse], visits: List[Visit]):
        self.nurses = nurses
        self.visits = visits
        self.scheduled_visits = []
    
    def solve(self) -> bool:
        """Simple greedy scheduling."""
        # Sort visits by priority and time window
        sorted_visits = sorted(
            self.visits, 
            key=lambda v: (v.priority, v.earliest_time)
        )
        
        # Track nurse assignments
        nurse_visits = {n.id: {"AM": [], "PM": []} for n in self.nurses}
        
        for visit in sorted_visits:
            assigned = False
            
            # Try to find best nurse
            for nurse in self.nurses:
                session = visit.session
                current_count = len(nurse_visits[nurse.id][session])
                max_count = nurse.max_visits_am if session == "AM" else nurse.max_visits_pm
                
                if current_count < max_count:
                    # Check continuity
                    if visit.requires_continuity and visit.continuity_group:
                        # Find if related visit is already assigned
                        for sv in self.scheduled_visits:
                            if sv.visit.continuity_group == visit.continuity_group:
                                if sv.nurse.id != nurse.id:
                                    continue  # Skip, need same nurse
                    
                    # Calculate scheduled time
                    if nurse_visits[nurse.id][session]:
                        last_visit = nurse_visits[nurse.id][session][-1]
                        travel_time = Config.SAME_ZONE_TRAVEL_TIME if last_visit.visit.patient.zone == visit.patient.zone else Config.DEFAULT_TRAVEL_TIME
                        scheduled_time = last_visit.scheduled_time + last_visit.visit.duration_minutes + travel_time
                    else:
                        scheduled_time = visit.earliest_time
                        travel_time = Config.HOSPITAL_RETURN_TIME
                    
                    # Ensure within time window
                    scheduled_time = max(scheduled_time, visit.earliest_time)
                    
                    if scheduled_time <= visit.latest_time:
                        sv = ScheduledVisit(
                            visit=visit,
                            nurse=nurse,
                            scheduled_time=scheduled_time,
                            travel_time_from_previous=travel_time,
                            sequence=len(nurse_visits[nurse.id][session])
                        )
                        self.scheduled_visits.append(sv)
                        nurse_visits[nurse.id][session].append(sv)
                        assigned = True
                        break
            
            if not assigned:
                # Could not assign - would go to vendor
                pass
        
        return len(self.scheduled_visits) > 0
    
    def get_schedule_by_nurse(self) -> Dict[str, List[ScheduledVisit]]:
        """Get schedule organized by nurse."""
        schedule = {nurse.id: [] for nurse in self.nurses}
        for sv in self.scheduled_visits:
            schedule[sv.nurse.id].append(sv)
        for nurse_id in schedule:
            schedule[nurse_id].sort(key=lambda x: x.scheduled_time)
        return schedule
    
    def calculate_metrics(self) -> Dict:
        """Calculate metrics."""
        return {
            'total_visits': len(self.scheduled_visits),
            'total_travel_time': sum(sv.travel_time_from_previous for sv in self.scheduled_visits),
            'visits_per_nurse': {
                n.name: len([sv for sv in self.scheduled_visits if sv.nurse.id == n.id])
                for n in self.nurses
            },
            'unassigned_visits': len(self.visits) - len(self.scheduled_visits)
        }


# ============================================================
# STREAMLIT UI
# ============================================================

def main():
    """Main Streamlit application."""
    
    # Header
    st.title("🏥 TTSH@Home Nurse Scheduling System")
    st.markdown("**Mobile Inpatient Care at Home - Automated Route Optimization**")
    
    # Sidebar
    st.sidebar.header("⚙️ Configuration")
    
    # Nurse configuration
    st.sidebar.subheader("👩‍⚕️ Available Nurses")
    num_nurses = st.sidebar.number_input("Number of nurses", min_value=1, max_value=5, value=2)
    
    nurses = []
    for i in range(num_nurses):
        with st.sidebar.expander(f"Nurse {i+1} Settings"):
            name = st.text_input(f"Name", value=f"Nurse {chr(65+i)}", key=f"nurse_name_{i}")
            languages = st.multiselect(
                "Languages",
                ["English", "Mandarin", "Malay", "Tamil", "Hokkien", "Cantonese"],
                default=["English"],
                key=f"nurse_lang_{i}"
            )
            nurses.append(Nurse(
                id=f"N{i:03d}",
                name=name,
                languages=languages
            ))
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Schedule", "🗺️ Route Map", "📊 Analytics"])
    
    # Tab 1: Upload and Schedule
    with tab1:
        st.header("Upload Patient Data")
        
        uploaded_file = st.file_uploader(
            "Upload Excel file with patient data",
            type=['xlsx', 'xls'],
            help="Excel file should have columns: Name, Location, Home Visit task/time, Session 2 task/time, Priority, Language"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.success(f"✅ Loaded {len(df)} patients")
                
                with st.expander("📋 Preview Data"):
                    st.dataframe(df)
                
                # Parse data
                parser = ExcelParser()
                patients, visits = parser.parse_dataframe(df)
                
                st.info(f"📊 Parsed: {len(patients)} patients, {len(visits)} visits")
                
                if parser.warnings:
                    with st.expander("⚠️ Parsing Warnings"):
                        for w in parser.warnings:
                            st.warning(w)
                
                # Run scheduler
                if st.button("🚀 Generate Schedule", type="primary"):
                    with st.spinner("Optimizing routes..."):
                        scheduler = SimpleScheduler(nurses=nurses, visits=visits)
                        success = scheduler.solve()
                        
                        if success:
                            st.success("✅ Schedule generated successfully!")
                            
                            # Store in session state
                            st.session_state['scheduler'] = scheduler
                            st.session_state['patients'] = patients
                            st.session_state['visits'] = visits
                            st.session_state['nurses'] = nurses
                            
                            # Show results
                            metrics = scheduler.calculate_metrics()
                            
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Total Visits", metrics['total_visits'])
                            col2.metric("Travel Time", f"{metrics['total_travel_time']} min")
                            col3.metric("Unassigned", metrics['unassigned_visits'])
                            col4.metric("Nurses", len(nurses))
                            
                            # Schedule table
                            st.subheader("📋 Generated Schedule")
                            
                            schedule = scheduler.get_schedule_by_nurse()
                            
                            for nurse in nurses:
                                nurse_visits = schedule[nurse.id]
                                
                                st.markdown(f"### 👩‍⚕️ {nurse.name} ({len(nurse_visits)} visits)")
                                
                                if nurse_visits:
                                    schedule_data = []
                                    for sv in nurse_visits:
                                        schedule_data.append({
                                            "Seq": sv.sequence + 1,
                                            "Time": minutes_to_time_string(sv.scheduled_time),
                                            "Patient": sv.visit.patient.name,
                                            "Procedure": sv.visit.procedure,
                                            "Zone": sv.visit.patient.zone,
                                            "Travel (min)": sv.travel_time_from_previous
                                        })
                                    st.dataframe(pd.DataFrame(schedule_data), use_container_width=True)
                                else:
                                    st.info("No visits assigned")
                            
                            # Export button
                            st.subheader("📥 Export Schedule")
                            
                            # Create export DataFrame
                            export_rows = []
                            for nurse in nurses:
                                for sv in schedule[nurse.id]:
                                    export_rows.append({
                                        'Nurse': nurse.name,
                                        'Sequence': sv.sequence + 1,
                                        'Scheduled Time': minutes_to_time_string(sv.scheduled_time),
                                        'Patient Name': sv.visit.patient.name,
                                        'Location': sv.visit.patient.address,
                                        'Zone': sv.visit.patient.zone,
                                        'Procedure': sv.visit.procedure,
                                        'Session': sv.visit.session,
                                        'Travel Time (min)': sv.travel_time_from_previous
                                    })
                            
                            export_df = pd.DataFrame(export_rows)
                            
                            # Excel download
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                export_df.to_excel(writer, index=False, sheet_name='Schedule')
                            
                            st.download_button(
                                label="📥 Download Schedule (Excel)",
                                data=buffer.getvalue(),
                                file_name=f"schedule_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                        else:
                            st.error("❌ Could not generate a feasible schedule")
            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
        
        else:
            # Show sample data option
            st.info("👆 Upload an Excel file to get started, or use sample data below")
            
            if st.button("📝 Use Sample Data"):
                # Create sample data
                sample_data = {
                    "Name": ["Tan AH", "Lim BK", "Wong CL", "Chen DM", "Lee EF", "Ng GH"],
                    "Location": [
                        "Blk 123 Ang Mo Kio Ave 4 S(560123)",
                        "Blk 456 Toa Payoh Lor 1 S(310456)",
                        "Blk 789 Hougang Ave 5 S(530789)",
                        "Blk 234 Bishan St 22 S(570234)",
                        "Blk 567 Woodlands Dr 14 S(730567)",
                        "Blk 890 Ang Mo Kio Ave 10 S(560890)"
                    ],
                    "Home Visit task/time": ["IV ABx 8 hrly", "Blood taking", "IV ABx", "Wound dressing", "Others (Priority) 10:00", "IV ABx"],
                    "Session 2 task/time": ["IV ABx 8 hrly (PM)", "", "", "", "", ""],
                    "Priority": ["Normal", "Normal", "Normal", "Normal", "Priority", "Normal"],
                    "Language": ["Mandarin", "English", "English", "Mandarin", "Malay", "English"]
                }
                sample_df = pd.DataFrame(sample_data)
                st.session_state['sample_df'] = sample_df
                st.dataframe(sample_df)
                st.rerun()
    
    # Tab 2: Route Map
    with tab2:
        st.header("🗺️ Route Visualization")
        
        if 'scheduler' in st.session_state:
            scheduler = st.session_state['scheduler']
            
            # Create map centered on TTSH
            m = folium.Map(
                location=[Config.HOSPITAL_LAT, Config.HOSPITAL_LNG],
                zoom_start=12,
                tiles='CartoDB positron'
            )
            
            # Add hospital marker
            folium.Marker(
                [Config.HOSPITAL_LAT, Config.HOSPITAL_LNG],
                popup='🏥 TTSH (Start/End)',
                icon=folium.Icon(color='red', icon='plus', prefix='fa')
            ).add_to(m)
            
            # Colors for nurses
            colors = ['blue', 'green', 'purple', 'orange', 'darkred']
            
            schedule = scheduler.get_schedule_by_nurse()
            
            for idx, nurse in enumerate(st.session_state['nurses']):
                nurse_visits = schedule[nurse.id]
                color = colors[idx % len(colors)]
                
                if not nurse_visits:
                    continue
                
                route_coords = [[Config.HOSPITAL_LAT, Config.HOSPITAL_LNG]]
                
                for sv in nurse_visits:
                    # Use approximate coordinates based on zone
                    zone_coords = {
                        "North": (1.42, 103.82),
                        "South": (1.27, 103.82),
                        "East": (1.35, 103.94),
                        "West": (1.35, 103.70),
                        "Central": (1.35, 103.85)
                    }
                    
                    lat, lng = zone_coords.get(sv.visit.patient.zone, (1.35, 103.85))
                    # Add some randomness
                    lat += np.random.uniform(-0.02, 0.02)
                    lng += np.random.uniform(-0.02, 0.02)
                    
                    route_coords.append([lat, lng])
                    
                    time_str = minutes_to_time_string(sv.scheduled_time)
                    popup_text = f"""
                        <b>{sv.visit.patient.name}</b><br>
                        Time: {time_str}<br>
                        Procedure: {sv.visit.procedure}<br>
                        Nurse: {nurse.name}
                    """
                    
                    folium.Marker(
                        [lat, lng],
                        popup=folium.Popup(popup_text, max_width=200),
                        icon=folium.Icon(color=color, icon='user', prefix='fa')
                    ).add_to(m)
                
                route_coords.append([Config.HOSPITAL_LAT, Config.HOSPITAL_LNG])
                
                folium.PolyLine(
                    route_coords,
                    weight=3,
                    color=color,
                    opacity=0.7,
                    popup=f"{nurse.name}'s Route"
                ).add_to(m)
            
            st_folium(m, width=800, height=500)
            
            # Legend
            st.markdown("**Legend:**")
            for idx, nurse in enumerate(st.session_state['nurses']):
                color = colors[idx % len(colors)]
                st.markdown(f"- 🔵 **{nurse.name}**" if color == 'blue' else f"- ⚫ **{nurse.name}**")
        
        else:
            st.info("👆 Generate a schedule first to see the route map")
    
    # Tab 3: Analytics
    with tab3:
        st.header("📊 Schedule Analytics")
        
        if 'scheduler' in st.session_state:
            scheduler = st.session_state['scheduler']
            metrics = scheduler.calculate_metrics()
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Visits per nurse chart
                fig = px.bar(
                    x=list(metrics['visits_per_nurse'].keys()),
                    y=list(metrics['visits_per_nurse'].values()),
                    title="Visits per Nurse",
                    labels={'x': 'Nurse', 'y': 'Number of Visits'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Zone distribution
                zone_counts = {}
                for sv in scheduler.scheduled_visits:
                    zone = sv.visit.patient.zone
                    zone_counts[zone] = zone_counts.get(zone, 0) + 1
                
                fig = px.pie(
                    values=list(zone_counts.values()),
                    names=list(zone_counts.keys()),
                    title="Visits by Zone"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Timeline visualization
            st.subheader("📅 Schedule Timeline")
            
            timeline_data = []
            for sv in scheduler.scheduled_visits:
                timeline_data.append({
                    'Nurse': sv.nurse.name,
                    'Patient': sv.visit.patient.name,
                    'Start': datetime(2024, 1, 1, sv.scheduled_time // 60, sv.scheduled_time % 60),
                    'End': datetime(2024, 1, 1, (sv.scheduled_time + sv.visit.duration_minutes) // 60, 
                                   (sv.scheduled_time + sv.visit.duration_minutes) % 60)
                })
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                
                fig = px.timeline(
                    timeline_df,
                    x_start='Start',
                    x_end='End',
                    y='Nurse',
                    color='Nurse',
                    hover_name='Patient',
                    title="Gantt Chart View"
                )
                fig.update_layout(xaxis_title="Time")
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.info("👆 Generate a schedule first to see analytics")
    
    # Footer
    st.markdown("---")
    st.markdown("*TTSH Mobile Inpatient Care at Home - Scheduling System v1.0*")


if __name__ == "__main__":
    main()
