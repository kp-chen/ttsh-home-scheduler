"""
Generate sample patient data for testing the scheduler.
Run this script to create sample_patient_data.xlsx
"""

import pandas as pd

def create_sample_data():
    """Create sample patient data matching TTSH Excel format."""
    
    data = {
        "Name": [
            "Tan AH",          # 8-hr IV patient (needs AM + PM)
            "Lim BK",          # Blood draw patient (must be early)
            "Wong CL",         # Regular IV patient
            "Chen DM",         # Regular wound care
            "Lee EF",          # Priority patient with fixed time
            "Ng GH",           # Regular IV
            "Goh IJ",          # Blood draw
            "Koh KL",          # 8-hr IV patient
            "Teo MN",          # Regular wound care
            "Ong PQ"           # Regular checkup
        ],
        "Location": [
            "Blk 123 Ang Mo Kio Ave 4 #08-123 S(560123)",      # AMK - North
            "Blk 456 Toa Payoh Lor 1 #05-456 S(310456)",       # Toa Payoh - Central
            "Blk 789 Hougang Ave 5 #12-789 S(530789)",         # Hougang - North-East
            "Blk 234 Bishan St 22 #03-234 S(570234)",          # Bishan - Central
            "Blk 567 Woodlands Dr 14 #07-567 S(730567)",       # Woodlands - North
            "Blk 890 Ang Mo Kio Ave 10 #11-890 S(560890)",     # AMK - North
            "Blk 345 Toa Payoh Lor 8 #02-345 S(310345)",       # Toa Payoh - Central
            "Blk 678 Serangoon Ave 2 #09-678 S(550678)",       # Serangoon - North-East
            "Blk 901 Bishan St 11 #06-901 S(570901)",          # Bishan - Central
            "Blk 432 Ang Mo Kio Ave 1 #04-432 S(560432)"       # AMK - North
        ],
        "Home Visit task/time": [
            "IV ABx 8 hrly",           # 8-hour IV - needs 2 visits
            "Blood taking",             # Must be done by 10 AM
            "IV ABx",                   # Regular IV
            "Wound dressing",           # Standard wound care
            "Others (Priority) 10:00",  # Fixed time priority
            "IV ABx",                   # Regular IV
            "Blood taking",             # Must be done by 10 AM
            "IV ABx 8 hrly",           # 8-hour IV - needs 2 visits
            "Wound dressing",           # Standard wound care
            "Vital signs"               # Regular checkup
        ],
        "Session 2 task/time": [
            "IV ABx 8 hrly (PM)",      # Second dose for 8-hr IV
            "",                          # No second visit
            "",                          # No second visit
            "",                          # No second visit
            "",                          # No second visit
            "",                          # No second visit
            "",                          # No second visit
            "IV ABx 8 hrly (PM)",      # Second dose for 8-hr IV
            "",                          # No second visit
            ""                           # No second visit
        ],
        "Priority": [
            "Normal",
            "Normal",
            "Normal",
            "Normal",
            "Priority",  # Fixed time patient
            "Normal",
            "Normal",
            "Normal",
            "Normal",
            "Normal"
        ],
        "Language": [
            "Mandarin",
            "English",
            "English",
            "Mandarin",
            "Malay",
            "English",
            "Mandarin",
            "English",
            "English",
            "Mandarin"
        ],
        "Notes": [
            "Prefer morning slot",
            "Fasting blood test",
            "",
            "Diabetic foot ulcer",
            "Needs interpreter",
            "",
            "Fasting blood test",
            "PICC line",
            "Post-surgical",
            "Elderly, lives alone"
        ]
    }
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Generate and save sample data
    df = create_sample_data()
    
    # Save to Excel
    output_path = "data/sample_patient_data.xlsx"
    df.to_excel(output_path, index=False, sheet_name="Patients")
    
    print(f"✅ Sample data saved to {output_path}")
    print(f"📊 Total patients: {len(df)}")
    print("\nPreview:")
    print(df[["Name", "Location", "Home Visit task/time", "Priority"]].to_string())
