import streamlit as st
import pandas as pd
from datetime import datetime, time
import gspread


# =========================
# Config
# =========================
APP_TITLE = "Sickle Cell ACS Audit Tool"

MONTH_OPTIONS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = list(range(CURRENT_YEAR - 10, CURRENT_YEAR + 1))

SEX_OPTIONS = ["Female", "Male", "Other", "Unknown"]

GENOTYPE_OPTIONS = [
    "HbSS",
    "HbSC",
    "HbS beta-zero thalassaemia",
    "HbS beta-plus thalassaemia",
    "Other",
    "Unknown",
]

ANALGESIA_OPTIONS = [
    "Not used",
    "Paracetamol",
    "Ibuprofen",
    "Diclofenac",
    "Oral morphine",
    "IV morphine",
    "Subcutaneous morphine",
    "Intranasal Fentanyl (INF)",
    "Oxycodone",
    "Fentanyl",
    "Morphine PCA",
    "Ketamine",
    "Other",
]

MAX_ANALGESIA_ENTRIES = 8

READMISSION_REASON_OPTIONS = [
    "Pain crisis / vaso-occlusive crisis",
    "Acute chest syndrome",
    "Infection",
    "Anaemia",
    "Other",
    "Unknown",
]

RESPIRATORY_REFERRAL_TIMING_OPTIONS = [
    "Not referred",
    "Reviewed during admission",
    "Outpatient referral within 6 months",
    "Outpatient referral after 6 months",
    "Unknown",
]

STEROID_OPTIONS = [
    "Dexamethasone",
    "Hydrocortisone",
    "Prednisolone",
    "Methylprednisolone",
    "Other",
]

STEROID_WEAN_OPTIONS = [
    "No wean",
    "Fixed course stopped",
    "Weaning course used",
    "Unknown",
]

ANTIBIOTIC_OPTIONS = [
    "Co-amoxiclav",
    "Phenoxymethylpenicillin (Calvepen)",
    "Ceftriaxone",
    "Cefotaxime",
    "Piperacillin-tazobactam / Tazocin",
    "Clarithromycin",
    "Erythromycin",
    "Azithromycin",
    "Vancomycin",
    "Gentamicin",
    "Meropenem",
    "Other",
]

RESPIRATORY_SUPPORT_OPTIONS = [
    "None",
    "Nasal cannula",
    "Simple face mask",
    "Venturi mask",
    "Non-rebreather mask",
    "High-flow nasal oxygen",
    "NIV",
    "Intubation / mechanical ventilation",
]

BACTERIA_OPTIONS = [
    "None isolated",
    "Streptococcus pneumoniae",
    "Haemophilus influenzae",
    "Mycoplasma pneumoniae",
    "Staphylococcus aureus",
    "Salmonella species",
    "Escherichia coli",
    "Other",
]

BLOODS_OPTIONS = [
    "FBC",
    "Reticulocyte count",
    "Renal / Electrolytes",
    "LDH",
    "CRP",
]

CULTURES_OPTIONS = [
    "Blood cultures",
    "Sputum cultures",
    "Nasopharyngeal aspirate",
    "Respiratory viral serology (including Chlamydia)",
]

ANTIVIRAL_OPTIONS = [
    "Not used",
    "Oseltamivir",
    "Other",
]

SECTIONS = {
    "Investigations": [
        {"label": "Bloods", "key": "bloods"},
        {"label": "CXR", "key": "cxr"},
        {"label": "Cultures", "key": "cultures"},
        {"label": "Group and Hold / Crossmatch", "key": "group_hold_cross"},
        {"label": "VBG", "key": "vbg"},
    ],
    "Treatment": [
        {"label": "Analgesia", "key": "analgesia"},
        {"label": "Steroids", "key": "steroids"},
        {"label": "Antibiotics", "key": "antibiotics"},
        {"label": "Antivirals", "key": "antivirals"},
        {"label": "Oxygen", "key": "oxygen"},
        {"label": "Fluids", "key": "fluids"},
        {"label": "Bronchodilators", "key": "bronchodilators"},
        {"label": "Simple Transfusion", "key": "simple_transfusion"},
        {"label": "Exchange Transfusion", "key": "exchange_transfusion"},
    ],
    "Discussions / Referrals": [
        {"label": "Discussion with Haematology", "key": "haematology_discussion"},
        {"label": "Discussion with ICU", "key": "icu_discussion"},
        {"label": "Respiratory Referral / Review", "key": "respiratory_referral"},
        {"label": "Respiratory Physiotherapy", "key": "respiratory_pt"},
    ],
}

ALL_TIMED_ITEMS = [item for section in SECTIONS.values() for item in section]

BACKGROUND_YN_FIELDS = [
    "influenza_vaccinated",
    "pneumococcal_vaccinated",
    "hib_vaccinated",
    "splenectomy",
    "liver_transplant",
    "bone_marrow_transplant",
    "hydroxyurea",
    "folic_acid",
    "vitamin_d",
    "phenoxymethylpenicillin_calvepen",
    "regular_transfusion_programme",
    "regular_venesection",
    "regular_exchange_transfusion_programme",
]


# =========================
# Password
# =========================
def check_password() -> bool:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title(APP_TITLE)
    password = st.text_input("Enter password", type="password")

    if st.button("Log in"):
        if password == st.secrets["app_password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    return False


# =========================
# Google Sheets
# =========================
@st.cache_resource
def get_sheet():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open("ACS Audit")
    return sh.sheet1


@st.cache_data(ttl=10)
def load_sheet_data():
    ws = get_sheet()
    return ws.get_all_records()


def find_existing_record(patient_id: str):
    """Look up a Research ID in the sheet. Returns the row dict, or None if not found."""
    patient_id = (patient_id or "").strip()
    if not patient_id:
        return None

    ws = get_sheet()
    headers = ws.row_values(1)

    if "Patient_ID" not in headers:
        return None

    col_idx = headers.index("Patient_ID") + 1
    col_values = ws.col_values(col_idx)

    for i, val in enumerate(col_values[1:], start=2):
        if val.strip() == patient_id:
            row_values = ws.row_values(i)
            # pad in case the row is shorter than the header row
            row_values += [""] * (len(headers) - len(row_values))
            return dict(zip(headers, row_values))

    return None


# =========================
# Reset helpers
# =========================
def reset_form_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    st.session_state["patient_id"] = ""
    st.session_state["editing_existing_id"] = None

    st.session_state["admission_month"] = MONTH_OPTIONS[now.month - 1]
    st.session_state["admission_year"] = now.year
    st.session_state["admission_time"] = now.time()

    st.session_state["discharge_day"] = 0
    st.session_state["discharge_time"] = now.time()

    st.session_state["age_at_admission"] = 0
    st.session_state["sex"] = "Unknown"
    st.session_state["genotype"] = "Unknown"
    st.session_state["genotype_other"] = ""

    for field in BACKGROUND_YN_FIELDS:
        st.session_state[field] = None
    st.session_state["background_notes"] = ""

    for item in ALL_TIMED_ITEMS:
        key = item["key"]
        st.session_state[f"{key}_day"] = 0
        st.session_state[f"{key}_time"] = now.time()
        st.session_state[f"{key}_performed"] = None

    reset_analgesia_entries(now.time())

    st.session_state["steroids_given"] = []
    st.session_state["steroids_other"] = ""
    st.session_state["steroid_max_dose_mg_per_kg"] = 0.0
    st.session_state["steroid_total_duration_days"] = 0
    st.session_state["steroid_weaning_protocol"] = "Unknown"
    st.session_state["steroid_wean_duration_days"] = 0
    st.session_state["steroid_notes"] = ""

    st.session_state["antibiotics_given"] = []
    st.session_state["antibiotic_dose_mg_per_kg"] = ""
    st.session_state["antibiotics_other"] = ""

    st.session_state["antiviral_drug"] = "Not used"
    st.session_state["antiviral_dose_mg_per_kg"] = 0.0
    st.session_state["antiviral_other"] = ""

    st.session_state["respiratory_referral_timing"] = "Not referred"
    st.session_state["respiratory_referral_notes"] = ""

    st.session_state["cxr_changes"] = None
    st.session_state["cxr_findings_notes"] = ""

    st.session_state["bloods_tests"] = []
    st.session_state["hb_at_admission"] = None

    st.session_state["cultures_sent"] = []

    st.session_state["temperature_at_admission"] = None
    st.session_state["respiratory_rate_at_admission"] = None
    st.session_state["o2_sats_at_admission"] = None
    st.session_state["pain_score_at_admission"] = None

    st.session_state["four_hourly_obs_performed"] = None
    st.session_state["four_hourly_obs_duration_hours"] = None

    st.session_state["highest_respiratory_support"] = "None"
    st.session_state["bacterium_isolated"] = None
    st.session_state["bacterium"] = "None isolated"
    st.session_state["bacterium_other"] = ""

    st.session_state["picu_admission"] = None
    st.session_state["developed_atelectasis"] = None
    st.session_state["death"] = None

    st.session_state["readmitted"] = None
    st.session_state["weeks_to_readmission"] = 0.0
    st.session_state["readmission_reason"] = "Unknown"
    st.session_state["readmission_reason_other"] = ""
    st.session_state["readmission_notes"] = ""


def handle_pending_reset() -> None:
    if st.session_state.get("reset_requested", False):
        reset_form_state()
        st.session_state["reset_requested"] = False


# =========================
# Time helpers
# =========================
def time_to_hours(selected_time) -> float | None:
    if selected_time is None:
        return None

    return selected_time.hour + selected_time.minute / 60


def calculate_hours_from_admission(admission_time, event_day, event_time):
    if admission_time is None or event_day is None or event_time is None:
        return None

    admission_hours = time_to_hours(admission_time)
    event_hours = event_day * 24 + time_to_hours(event_time)

    if admission_hours is None or event_hours is None:
        return None

    return round(event_hours - admission_hours, 2)


def calculate_length_of_stay(admission_time, discharge_day, discharge_time):
    if admission_time is None or discharge_day is None or discharge_time is None:
        return None, None

    admission_hours = time_to_hours(admission_time)
    discharge_hours = discharge_day * 24 + time_to_hours(discharge_time)

    if admission_hours is None or discharge_hours is None:
        return None, None

    los_hours = round(discharge_hours - admission_hours, 2)
    los_days = round(los_hours / 24, 2)

    return los_hours, los_days


def serialise_multiselect(values):
    if not values:
        return ""
    return "; ".join(values)


# =========================
# Parsing helpers (for loading existing records back into the form)
# =========================
def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def yes_no_button(label: str, key: str, **kwargs):
    """Render a Yes/No button selector with NO default selection.
    Returns 'Yes', 'No', or None if the person hasn't answered yet.
    Unanswered stays visually distinct from 'No' - it is not pre-filled."""
    return st.radio(label, options=["Yes", "No"], key=key, index=None, horizontal=True, **kwargs)


def yn_to_bool(value):
    """Convert a Yes/No/None widget value to True/False/None for storage."""
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def bool_to_yn(value):
    """Convert a stored True/False/None value back to 'Yes'/'No'/None for the widget."""
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return None


def parse_yn_from_sheet(value):
    """Parse a saved sheet cell (which may be blank, 'True'/'False', or already
    'Yes'/'No') back into 'Yes'/'No'/None for populating a Yes/No button widget."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "":
        return None
    if text in {"true", "yes", "1"}:
        return "Yes"
    if text in {"false", "no", "0"}:
        return "No"
    return None


def parse_int(value, default=0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_time_value(value, fallback):
    if not value or str(value).strip() == "":
        return fallback
    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return fallback


def parse_multiselect(value, options):
    if not value:
        return []
    items = [v.strip() for v in str(value).split(";") if v.strip()]
    return [item for item in items if item in options]


def apply_record_to_session_state(record: dict) -> None:
    """Populate session state (i.e. the form) from a previously saved sheet row."""
    now_time = datetime.now().replace(second=0, microsecond=0).time()

    st.session_state["patient_id"] = record.get("Patient_ID", "")

    if record.get("Admission_Month") in MONTH_OPTIONS:
        st.session_state["admission_month"] = record["Admission_Month"]

    admission_year = parse_int(record.get("Admission_Year"), CURRENT_YEAR)
    if admission_year in YEAR_OPTIONS:
        st.session_state["admission_year"] = admission_year

    admission_time = parse_time_value(record.get("Admission_Time"), now_time)
    st.session_state["admission_time"] = admission_time

    st.session_state["discharge_day"] = parse_int(record.get("Discharge_Day"), 0)
    st.session_state["discharge_time"] = parse_time_value(record.get("Discharge_Time"), admission_time)

    st.session_state["age_at_admission"] = parse_int(record.get("age_at_admission"), 0)

    if record.get("sex") in SEX_OPTIONS:
        st.session_state["sex"] = record["sex"]

    if record.get("genotype") in GENOTYPE_OPTIONS:
        st.session_state["genotype"] = record["genotype"]

    st.session_state["genotype_other"] = record.get("genotype_other", "")

    for k in BACKGROUND_YN_FIELDS:
        st.session_state[k] = parse_yn_from_sheet(record.get(k))

    st.session_state["background_notes"] = record.get("background_notes", "")

    # Timed sections (Investigations, Treatment, Discussions/Referrals)
    for section_items in SECTIONS.values():
        for item in section_items:
            key = item["key"]
            label = item["label"]
            safe_label = label.replace(" ", "_").replace("/", "_")

            st.session_state[f"{key}_performed"] = parse_yn_from_sheet(record.get(f"{safe_label}_Performed"))
            st.session_state[f"{key}_day"] = parse_int(record.get(f"{safe_label}_Day"), 0)
            st.session_state[f"{key}_time"] = parse_time_value(
                record.get(f"{safe_label}_Time"), admission_time
            )

    # Analgesia
    load_analgesia_entries_from_record(record, admission_time)

    # Steroids
    st.session_state["steroids_given"] = parse_multiselect(record.get("Steroids_given"), STEROID_OPTIONS)
    st.session_state["steroids_other"] = record.get("Steroids_other", "")
    st.session_state["steroid_max_dose_mg_per_kg"] = parse_float(record.get("Steroid_max_dose_mg_per_kg"), 0.0)
    st.session_state["steroid_total_duration_days"] = parse_int(record.get("Steroid_total_duration_days"), 0)

    weaning = record.get("Steroid_weaning_protocol", "Unknown")
    st.session_state["steroid_weaning_protocol"] = (
        weaning if weaning in STEROID_WEAN_OPTIONS else "Unknown"
    )
    st.session_state["steroid_wean_duration_days"] = parse_int(record.get("Steroid_wean_duration_days"), 0)
    st.session_state["steroid_notes"] = record.get("Steroid_notes", "")

    # Antibiotics
    st.session_state["antibiotics_given"] = parse_multiselect(record.get("Antibiotics_given"), ANTIBIOTIC_OPTIONS)
    st.session_state["antibiotic_dose_mg_per_kg"] = record.get("Antibiotic_dose_mg_per_kg", "")
    st.session_state["antibiotics_other"] = record.get("Antibiotics_other", "")

    # Antivirals
    antiviral_drug = record.get("Antiviral_Drug", "Not used")
    st.session_state["antiviral_drug"] = antiviral_drug if antiviral_drug in ANTIVIRAL_OPTIONS else "Not used"
    st.session_state["antiviral_dose_mg_per_kg"] = parse_float(record.get("Antiviral_Dose_mg_per_kg"), 0.0)
    st.session_state["antiviral_other"] = record.get("Antiviral_Other", "")

    # Respiratory referral
    resp_timing = record.get("Respiratory_referral_timing", "Not referred")
    st.session_state["respiratory_referral_timing"] = (
        resp_timing if resp_timing in RESPIRATORY_REFERRAL_TIMING_OPTIONS[1:]
        else RESPIRATORY_REFERRAL_TIMING_OPTIONS[1]
    )
    st.session_state["respiratory_referral_notes"] = record.get("Respiratory_referral_notes", "")

    # CXR
    st.session_state["cxr_changes"] = parse_yn_from_sheet(record.get("CXR_Changes"))
    st.session_state["cxr_findings_notes"] = record.get("CXR_Findings_Notes", "")

    # Bloods
    st.session_state["bloods_tests"] = parse_multiselect(record.get("Bloods_Tests"), BLOODS_OPTIONS)
    hb_val = record.get("Hb_at_Admission")
    st.session_state["hb_at_admission"] = float(hb_val) if hb_val not in (None, "") else None

    # Cultures
    st.session_state["cultures_sent"] = parse_multiselect(record.get("Cultures_Sent"), CULTURES_OPTIONS)

    # Admission observations
    def _load_optional_float(field_name):
        val = record.get(field_name)
        return float(val) if val not in (None, "") else None

    def _load_optional_int(field_name):
        val = record.get(field_name)
        try:
            return int(float(val)) if val not in (None, "") else None
        except (TypeError, ValueError):
            return None

    st.session_state["temperature_at_admission"] = _load_optional_float("temperature_at_admission")
    st.session_state["respiratory_rate_at_admission"] = _load_optional_int("respiratory_rate_at_admission")
    st.session_state["o2_sats_at_admission"] = _load_optional_int("o2_sats_at_admission")
    st.session_state["pain_score_at_admission"] = _load_optional_int("pain_score_at_admission")

    st.session_state["four_hourly_obs_performed"] = parse_yn_from_sheet(record.get("four_hourly_obs_performed"))
    st.session_state["four_hourly_obs_duration_hours"] = _load_optional_float("four_hourly_obs_duration_hours")

    # Microbiology
    st.session_state["bacterium_isolated"] = parse_yn_from_sheet(record.get("bacterium_isolated"))
    bacterium = record.get("bacterium", "None isolated")
    st.session_state["bacterium"] = bacterium if bacterium in BACTERIA_OPTIONS else "None isolated"
    st.session_state["bacterium_other"] = record.get("bacterium_other", "")

    # Outcome
    resp_support = record.get("highest_respiratory_support", "None")
    st.session_state["highest_respiratory_support"] = (
        resp_support if resp_support in RESPIRATORY_SUPPORT_OPTIONS else "None"
    )
    st.session_state["picu_admission"] = parse_yn_from_sheet(record.get("picu_admission"))
    st.session_state["developed_atelectasis"] = parse_yn_from_sheet(record.get("developed_atelectasis"))
    st.session_state["death"] = parse_yn_from_sheet(record.get("death"))
    st.session_state["readmitted"] = parse_yn_from_sheet(record.get("readmitted"))
    st.session_state["weeks_to_readmission"] = parse_float(record.get("weeks_to_readmission"), 0.0)

    readmission_reason = record.get("readmission_reason", "Unknown")
    st.session_state["readmission_reason"] = (
        readmission_reason if readmission_reason in READMISSION_REASON_OPTIONS else "Unknown"
    )
    st.session_state["readmission_reason_other"] = record.get("readmission_reason_other", "")
    st.session_state["readmission_notes"] = record.get("readmission_notes", "")

    st.session_state["editing_existing_id"] = record.get("Patient_ID", "")


def on_patient_id_change() -> None:
    """Callback fired when the Research ID field changes and loses focus
    (i.e. after pressing Enter or Tab). Automatically looks up and loads
    any existing record for that ID."""
    target_id = st.session_state.get("patient_id", "").strip()

    if not target_id:
        st.session_state["editing_existing_id"] = None
        st.session_state["load_message"] = None
        return

    try:
        record = find_existing_record(target_id)
    except Exception as e:
        st.session_state["load_message"] = ("error", f"Could not search the sheet: {e}")
        return

    if record:
        apply_record_to_session_state(record)
        st.session_state["load_message"] = (
            "success",
            f"Loaded existing record for Research ID '{target_id}'. Continue filling in the remaining fields below.",
        )
    else:
        st.session_state["editing_existing_id"] = None
        st.session_state["load_message"] = (
            "info",
            f"No existing record found for '{target_id}'. Starting a new entry — this ID hasn't been used yet.",
        )


def handle_new_record_request() -> None:
    if st.session_state.get("new_record_requested", False):
        st.session_state["new_record_requested"] = False
        reset_form_state()
        st.session_state["load_message"] = None


# =========================
# Session state helpers
# =========================
def initialise_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    defaults = {
        "patient_id": "",
        "reset_requested": False,
        "new_record_requested": False,
        "editing_existing_id": None,
        "load_message": None,

        "admission_month": MONTH_OPTIONS[now.month - 1],
        "admission_year": now.year,
        "admission_time": now.time(),
        "discharge_day": 0,
        "discharge_time": now.time(),

        "age_at_admission": 0,
        "sex": "Unknown",
        "genotype": "Unknown",
        "genotype_other": "",

        "influenza_vaccinated": None,
        "pneumococcal_vaccinated": None,
        "hib_vaccinated": None,

        "splenectomy": None,
        "liver_transplant": None,
        "bone_marrow_transplant": None,

        "hydroxyurea": None,
        "folic_acid": None,
        "vitamin_d": None,
        "phenoxymethylpenicillin_calvepen": None,
        "regular_transfusion_programme": None,
        "regular_venesection": None,
        "regular_exchange_transfusion_programme": None,
        "background_notes": "",

        "steroids_given": [],
        "steroids_other": "",
        "steroid_max_dose_mg_per_kg": 0.0,
        "steroid_total_duration_days": 0,
        "steroid_weaning_protocol": "Unknown",
        "steroid_wean_duration_days": 0,
        "steroid_notes": "",

        "antibiotics_given": [],
        "antibiotic_dose_mg_per_kg": "",
        "antibiotics_other": "",

        "antiviral_drug": "Not used",
        "antiviral_dose_mg_per_kg": 0.0,
        "antiviral_other": "",

        "respiratory_referral_timing": "Not referred",
        "respiratory_referral_notes": "",

        "cxr_changes": None,
        "cxr_findings_notes": "",

        "bloods_tests": [],
        "hb_at_admission": None,

        "cultures_sent": [],

        "temperature_at_admission": None,
        "respiratory_rate_at_admission": None,
        "o2_sats_at_admission": None,
        "pain_score_at_admission": None,

        "four_hourly_obs_performed": None,
        "four_hourly_obs_duration_hours": None,

        "highest_respiratory_support": "None",
        "bacterium_isolated": None,
        "bacterium": "None isolated",
        "bacterium_other": "",

        "picu_admission": None,
        "developed_atelectasis": None,
        "death": None,

        "readmitted": None,
        "weeks_to_readmission": 0.0,
        "readmission_reason": "Unknown",
        "readmission_reason_other": "",
        "readmission_notes": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    for item in ALL_TIMED_ITEMS:
        key = item["key"]

        if f"{key}_day" not in st.session_state:
            st.session_state[f"{key}_day"] = 0

        if f"{key}_time" not in st.session_state:
            st.session_state[f"{key}_time"] = st.session_state["admission_time"]

        if f"{key}_performed" not in st.session_state:
            st.session_state[f"{key}_performed"] = None

    ensure_analgesia_entries_initialised()


def init_analgesia_entry_defaults(entry_id: int, entry_time=None) -> None:
    fallback_time = entry_time or st.session_state.get("admission_time", datetime.now().time())
    st.session_state[f"analgesia_entry_{entry_id}_line"] = "Not used"
    st.session_state[f"analgesia_entry_{entry_id}_dose"] = 0.0
    st.session_state[f"analgesia_entry_{entry_id}_other"] = ""
    st.session_state[f"analgesia_entry_{entry_id}_day"] = 0
    st.session_state[f"analgesia_entry_{entry_id}_time"] = fallback_time


def ensure_analgesia_entries_initialised() -> None:
    if "analgesia_entry_ids" not in st.session_state:
        st.session_state["analgesia_entry_ids"] = [1]
        st.session_state["analgesia_next_id"] = 2
        init_analgesia_entry_defaults(1)


def reset_analgesia_entries(default_time) -> None:
    st.session_state["analgesia_entry_ids"] = [1]
    st.session_state["analgesia_next_id"] = 2
    init_analgesia_entry_defaults(1, default_time)


def add_analgesia_entry() -> None:
    if len(st.session_state["analgesia_entry_ids"]) >= MAX_ANALGESIA_ENTRIES:
        return
    new_id = st.session_state["analgesia_next_id"]
    st.session_state["analgesia_entry_ids"].append(new_id)
    st.session_state["analgesia_next_id"] += 1
    init_analgesia_entry_defaults(new_id)


def load_analgesia_entries_from_record(record: dict, admission_time) -> None:
    entries = []

    for i in range(1, MAX_ANALGESIA_ENTRIES + 1):
        drug = record.get(f"Analgesia_{i}_Drug", "")
        if drug and drug != "Not used":
            entries.append({
                "drug": drug,
                "dose": record.get(f"Analgesia_{i}_Dose", ""),
                "other": record.get(f"Analgesia_{i}_Other", ""),
                "day": record.get(f"Analgesia_{i}_Day"),
                "time": record.get(f"Analgesia_{i}_Time"),
            })

    if not entries:
        reset_analgesia_entries(admission_time)
        return

    ids = []
    next_id = 1

    for entry in entries:
        entry_id = next_id
        ids.append(entry_id)
        next_id += 1

        drug = entry.get("drug", "Not used")
        st.session_state[f"analgesia_entry_{entry_id}_line"] = (
            drug if drug in ANALGESIA_OPTIONS else "Not used"
        )
        st.session_state[f"analgesia_entry_{entry_id}_dose"] = parse_float(
            entry.get("dose"), 0.0
        )
        st.session_state[f"analgesia_entry_{entry_id}_other"] = entry.get("other", "")
        st.session_state[f"analgesia_entry_{entry_id}_day"] = parse_int(entry.get("day"), 0)
        st.session_state[f"analgesia_entry_{entry_id}_time"] = parse_time_value(
            entry.get("time"), admission_time
        )

    st.session_state["analgesia_entry_ids"] = ids
    st.session_state["analgesia_next_id"] = next_id


def sync_interventions_to_admission() -> None:
    admission_time = st.session_state["admission_time"]

    for item in ALL_TIMED_ITEMS:
        key = item["key"]
        st.session_state[f"{key}_day"] = 0
        st.session_state[f"{key}_time"] = admission_time

    ensure_analgesia_entries_initialised()
    for entry_id in st.session_state["analgesia_entry_ids"]:
        st.session_state[f"analgesia_entry_{entry_id}_day"] = 0
        st.session_state[f"analgesia_entry_{entry_id}_time"] = admission_time


# =========================
# UI sections
# =========================
def render_header() -> None:
    st.title(APP_TITLE)
    st.caption("No specific admission, discharge, date of birth, or intervention dates are collected.")

    if st.session_state.get("submitted"):
        action = st.session_state.get("last_save_action", "created")
        if action == "updated":
            st.success("✅ Existing record updated successfully")
        else:
            st.success("✅ New record saved successfully")
        st.session_state["submitted"] = False

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.5rem;
        }

        h1 {
            font-size: 2.8rem !important;
        }

        h2 {
            font-size: 2.0rem !important;
            margin-top: 2rem !important;
        }

        h3 {
            font-size: 1.35rem !important;
            margin-top: 1rem !important;
        }

        div[data-testid="stExpander"] details summary p {
            font-size: 1.05rem !important;
        }

        .small-note {
            font-size: 0.95rem;
            opacity: 0.8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_patient_section():
    st.header("Patient Information")

    with st.container(border=True):
        id_col, new_col = st.columns([3, 1])

        with id_col:
            patient_id = st.text_input(
                "Research ID",
                key="patient_id",
                on_change=on_patient_id_change,
            )

        with new_col:
            st.write("")
            st.write("")
            if st.button("🆕 Start New / Clear", use_container_width=True):
                st.session_state["new_record_requested"] = True
                st.rerun()

        if st.session_state.get("load_message"):
            level, message = st.session_state["load_message"]
            getattr(st, level)(message)

        if st.session_state.get("editing_existing_id"):
            st.info(
                f"📝 You are editing the existing record for Research ID "
                f"'{st.session_state['editing_existing_id']}'. Submitting will update "
                f"that record rather than create a new one."
            )

        col1, col2, col3 = st.columns(3)

        with col1:
            admission_month = st.selectbox(
                "Admission Month",
                options=MONTH_OPTIONS,
                key="admission_month",
            )

        with col2:
            admission_year = st.selectbox(
                "Admission Year",
                options=YEAR_OPTIONS,
                key="admission_year",
            )

        with col3:
            admission_time = st.time_input(
                "Registration Time",
                key="admission_time",
                on_change=sync_interventions_to_admission,
            )

        st.markdown("### Discharge")

        dcol1, dcol2 = st.columns(2)

        with dcol1:
            discharge_day = st.number_input(
                "Discharge Day",
                min_value=0,
                max_value=365,
                step=1,
                key="discharge_day",
                help="Day 0 = day of admission. Day 1 = next day.",
            )

        with dcol2:
            discharge_time = st.time_input(
                "Discharge Time",
                key="discharge_time",
            )

    return patient_id, admission_month, admission_year, admission_time, discharge_day, discharge_time


def render_admission_observations_section() -> dict:
    st.header("Admission Observations")
    values = {}

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            values["temperature_at_admission"] = st.number_input(
                "Temperature, °C",
                min_value=30.0,
                max_value=43.0,
                step=0.1,
                key="temperature_at_admission",
            )

        with col2:
            values["respiratory_rate_at_admission"] = st.number_input(
                "Respiratory rate, breaths/min",
                min_value=0,
                max_value=100,
                step=1,
                key="respiratory_rate_at_admission",
            )

        with col3:
            values["o2_sats_at_admission"] = st.number_input(
                "O2 saturation, %",
                min_value=0,
                max_value=100,
                step=1,
                key="o2_sats_at_admission",
            )

        with col4:
            values["pain_score_at_admission"] = st.number_input(
                "Pain score (0-10)",
                min_value=0,
                max_value=10,
                step=1,
                key="pain_score_at_admission",
            )

        st.markdown("**4-hourly observations**")
        mcol1, mcol2 = st.columns(2)

        with mcol1:
            values["four_hourly_obs_performed"] = yes_no_button(
                "4-hourly monitoring performed?",
                key="four_hourly_obs_performed",
            )

        with mcol2:
            values["four_hourly_obs_duration_hours"] = st.number_input(
                "Duration maintained, hours",
                min_value=0.0,
                max_value=500.0,
                step=1.0,
                key="four_hourly_obs_duration_hours",
                disabled=values["four_hourly_obs_performed"] != "Yes",
            )

    return values


def render_background_section() -> dict:
    st.header("Background")
    values = {}

    with st.container(border=True):
        st.markdown("**Patient phenotype**")
        col1, col2, col3 = st.columns(3)

        with col1:
            values["age_at_admission"] = st.number_input(
                "Age at Admission",
                min_value=0,
                max_value=120,
                step=1,
                key="age_at_admission",
            )

        with col2:
            values["sex"] = st.selectbox(
                "Sex",
                options=SEX_OPTIONS,
                key="sex",
            )

        with col3:
            values["genotype"] = st.selectbox(
                "Sickle Cell Genotype",
                options=GENOTYPE_OPTIONS,
                key="genotype",
            )

        if values["genotype"] == "Other":
            values["genotype_other"] = st.text_input(
                "Specify other genotype",
                key="genotype_other",
            )
        else:
            values["genotype_other"] = ""

        st.markdown("**Vaccination status**")
        vacc_col1, vacc_col2, vacc_col3 = st.columns(3)

        with vacc_col1:
            values["influenza_vaccinated"] = yes_no_button(
                "Influenza",
                key="influenza_vaccinated",
            )

        with vacc_col2:
            values["pneumococcal_vaccinated"] = yes_no_button(
                "Pneumococcal",
                key="pneumococcal_vaccinated",
            )

        with vacc_col3:
            values["hib_vaccinated"] = yes_no_button(
                "Haemophilus influenzae type B",
                key="hib_vaccinated",
            )

        st.markdown("**Previous procedures**")
        hist_col1, hist_col2, hist_col3 = st.columns(3)

        with hist_col1:
            values["splenectomy"] = yes_no_button(
                "Splenectomy",
                key="splenectomy",
            )

        with hist_col2:
            values["liver_transplant"] = yes_no_button(
                "Liver transplant",
                key="liver_transplant",
            )

        with hist_col3:
            values["bone_marrow_transplant"] = yes_no_button(
                "Bone marrow transplant",
                key="bone_marrow_transplant",
            )

        st.markdown("**Admission medications**")
        med_col1, med_col2, med_col3 = st.columns(3)

        with med_col1:
            values["hydroxyurea"] = yes_no_button("Hydroxyurea", key="hydroxyurea")
            values["folic_acid"] = yes_no_button("Folic acid", key="folic_acid")

        with med_col2:
            values["vitamin_d"] = yes_no_button("Vitamin D", key="vitamin_d")
            values["phenoxymethylpenicillin_calvepen"] = yes_no_button(
                "Phenoxymethylpenicillin (Calvepen)",
                key="phenoxymethylpenicillin_calvepen",
            )

        with med_col3:
            values["regular_transfusion_programme"] = yes_no_button(
                "Regular transfusion programme",
                key="regular_transfusion_programme",
            )
            values["regular_venesection"] = yes_no_button(
                "Regular venesection",
                key="regular_venesection",
            )
            values["regular_exchange_transfusion_programme"] = yes_no_button(
                "Regular exchange transfusion programme",
                key="regular_exchange_transfusion_programme",
            )

        values["background_notes"] = st.text_area(
            "Other background notes",
            key="background_notes",
            height=80,
        )

    return values


def empty_treatment_details(key: str) -> dict:
    if key == "analgesia":
        return {
            "Analgesia_Entries": [],
        }

    if key == "steroids":
        return {
            "Steroids_given": "",
            "Steroids_other": "",
            "Steroid_max_dose_mg_per_kg": "",
            "Steroid_total_duration_days": "",
            "Steroid_weaning_protocol": "",
            "Steroid_wean_duration_days": "",
            "Steroid_notes": "",
        }

    if key == "antibiotics":
        return {
            "Antibiotics_given": "",
            "Antibiotic_dose_mg_per_kg": "",
            "Antibiotics_other": "",
        }

    if key == "respiratory_referral":
        return {
            "Respiratory_referral_timing": "",
            "Respiratory_referral_notes": "",
        }

    if key == "cxr":
        return {
            "CXR_Changes": "",
            "CXR_Findings_Notes": "",
        }

    if key == "bloods":
        return {
            "Bloods_Tests": "",
            "Hb_at_Admission": "",
        }

    if key == "cultures":
        return {
            "Cultures_Sent": "",
        }

    if key == "antivirals":
        return {
            "Antiviral_Drug": "",
            "Antiviral_Dose_mg_per_kg": "",
            "Antiviral_Other": "",
        }

    return {}


def render_analgesia_entry(entry_id: int, entry_number: int) -> dict:
    col1, col2, col3, col4, col5 = st.columns([1.8, 1, 1, 1.2, 0.6])

    with col1:
        analgesia_choice = st.selectbox(
            f"Entry {entry_number} drug",
            options=ANALGESIA_OPTIONS,
            key=f"analgesia_entry_{entry_id}_line",
            on_change=lambda eid=entry_id: st.session_state.update(
                {f"analgesia_entry_{eid}_dose": 0.0}
            ),
        )

    not_used = analgesia_choice == "Not used"
    is_ibuprofen = analgesia_choice == "Ibuprofen"
    dose_unit = "mg" if is_ibuprofen else "mg/kg"

    with col2:
        if is_ibuprofen:
            dose = st.number_input(
                f"Entry {entry_number} dose, mg",
                min_value=0.0,
                max_value=1000.0,
                step=5.0,
                key=f"analgesia_entry_{entry_id}_dose",
                disabled=not_used,
            )
        else:
            dose = st.number_input(
                f"Entry {entry_number} dose, mg/kg",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                key=f"analgesia_entry_{entry_id}_dose",
                disabled=not_used,
            )

    with col3:
        day = st.number_input(
            f"Entry {entry_number} day",
            min_value=0,
            max_value=365,
            step=1,
            key=f"analgesia_entry_{entry_id}_day",
            disabled=not_used,
        )

    with col4:
        given_time = st.time_input(
            f"Entry {entry_number} time",
            key=f"analgesia_entry_{entry_id}_time",
            disabled=not_used,
        )

    with col5:
        st.write("")
        st.write("")
        remove_clicked = st.button("🗑️", key=f"analgesia_entry_{entry_id}_remove")

    if analgesia_choice == "Other":
        other = st.text_input(
            f"Specify other drug for entry {entry_number}",
            key=f"analgesia_entry_{entry_id}_other",
        )
    else:
        other = ""

    return {
        "drug": analgesia_choice,
        "dose": "" if not_used else dose,
        "dose_unit": "" if not_used else dose_unit,
        "other": other,
        "day": None if not_used else day,
        "time": None if not_used else given_time,
        "remove_clicked": remove_clicked,
    }


def render_analgesia_entries() -> list:
    ensure_analgesia_entries_initialised()

    entries = []
    remove_id = None

    for idx, entry_id in enumerate(st.session_state["analgesia_entry_ids"], start=1):
        entry = render_analgesia_entry(entry_id, idx)
        entries.append(entry)

        if entry["remove_clicked"]:
            remove_id = entry_id

    if remove_id is not None and len(st.session_state["analgesia_entry_ids"]) > 1:
        st.session_state["analgesia_entry_ids"].remove(remove_id)
        st.rerun()

    if len(st.session_state["analgesia_entry_ids"]) < MAX_ANALGESIA_ENTRIES:
        if st.button("➕ Add analgesia entry", key="add_analgesia_entry_btn"):
            add_analgesia_entry()
            st.rerun()
    else:
        st.caption(f"Maximum of {MAX_ANALGESIA_ENTRIES} analgesia entries reached.")

    return entries


def render_treatment_details(key: str) -> dict:
    details = empty_treatment_details(key)

    if key == "analgesia":
        st.markdown("#### Analgesia details")

        details["Analgesia_Entries"] = render_analgesia_entries()

    elif key == "steroids":
        st.markdown("#### Steroid details")

        col1, col2 = st.columns(2)

        with col1:
            details["Steroids_given"] = st.multiselect(
                "Steroid given",
                options=STEROID_OPTIONS,
                key="steroids_given",
            )

            if "Other" in details["Steroids_given"]:
                details["Steroids_other"] = st.text_input(
                    "Specify other steroid",
                    key="steroids_other",
                )
            else:
                details["Steroids_other"] = ""

        with col2:
            details["Steroid_max_dose_mg_per_kg"] = st.number_input(
                "Maximum steroid dose, mg/kg",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                key="steroid_max_dose_mg_per_kg",
            )

        col3, col4, col5 = st.columns(3)

        with col3:
            details["Steroid_total_duration_days"] = st.number_input(
                "Total steroid duration, days",
                min_value=0,
                max_value=120,
                step=1,
                key="steroid_total_duration_days",
            )

        with col4:
            details["Steroid_weaning_protocol"] = st.selectbox(
                "Steroid weaning approach",
                options=STEROID_WEAN_OPTIONS,
                key="steroid_weaning_protocol",
            )

        with col5:
            details["Steroid_wean_duration_days"] = st.number_input(
                "Wean duration, days",
                min_value=0,
                max_value=120,
                step=1,
                key="steroid_wean_duration_days",
                disabled=details["Steroid_weaning_protocol"] != "Weaning course used",
            )

            if details["Steroid_weaning_protocol"] != "Weaning course used":
                details["Steroid_wean_duration_days"] = ""

        details["Steroid_notes"] = st.text_area(
            "Steroid notes / protocol details",
            key="steroid_notes",
            height=70,
            placeholder="Optional. For example, dose reductions or local protocol wording.",
        )

    elif key == "antibiotics":
        st.markdown("#### Antibiotic details")
        details["Antibiotics_given"] = st.multiselect(
            "Antibiotics given",
            options=ANTIBIOTIC_OPTIONS,
            key="antibiotics_given",
        )

        details["Antibiotic_dose_mg_per_kg"] = st.text_input(
            "Antibiotic dose(s), mg/kg",
            key="antibiotic_dose_mg_per_kg",
            placeholder="e.g. ceftriaxone 50 mg/kg; azithromycin 10 mg/kg",
        )

        if "Other" in details["Antibiotics_given"]:
            details["Antibiotics_other"] = st.text_input(
                "Specify other antibiotic",
                key="antibiotics_other",
            )
        else:
            details["Antibiotics_other"] = ""

    elif key == "respiratory_referral":
        st.markdown("#### Respiratory referral / review details")

        col1, col2 = st.columns(2)

        with col1:
            details["Respiratory_referral_timing"] = st.selectbox(
                "Respiratory input",
                options=RESPIRATORY_REFERRAL_TIMING_OPTIONS[1:],
                key="respiratory_referral_timing",
            )

        with col2:
            details["Respiratory_referral_notes"] = st.text_area(
                "Respiratory referral / review notes",
                key="respiratory_referral_notes",
                height=80,
                placeholder="Optional. For example, reviewed during admission, outpatient referral requested, or reason not referred.",
            )

    elif key == "cxr":
        st.markdown("#### CXR details")

        col1, col2 = st.columns(2)

        with col1:
            cxr_changes_yn = yes_no_button("Any changes on CXR?", key="cxr_changes")
            details["CXR_Changes"] = cxr_changes_yn

        with col2:
            details["CXR_Findings_Notes"] = st.text_area(
                "Findings",
                key="cxr_findings_notes",
                height=80,
                disabled=cxr_changes_yn != "Yes",
                placeholder="Optional. E.g. new infiltrate, location, bilateral/unilateral.",
            )

    elif key == "bloods":
        st.markdown("#### Bloods details")

        col1, col2 = st.columns(2)

        with col1:
            details["Bloods_Tests"] = st.multiselect(
                "Which bloods were taken",
                options=BLOODS_OPTIONS,
                key="bloods_tests",
            )

        with col2:
            details["Hb_at_Admission"] = st.number_input(
                "Hb at admission, g/dL",
                min_value=0.0,
                max_value=25.0,
                step=0.1,
                key="hb_at_admission",
            )

    elif key == "cultures":
        st.markdown("#### Cultures details")

        details["Cultures_Sent"] = st.multiselect(
            "Which cultures were sent",
            options=CULTURES_OPTIONS,
            key="cultures_sent",
        )

    elif key == "antivirals":
        st.markdown("#### Antiviral details")

        col1, col2 = st.columns(2)

        with col1:
            antiviral_choice = st.selectbox(
                "Antiviral drug",
                options=ANTIVIRAL_OPTIONS,
                key="antiviral_drug",
            )
            details["Antiviral_Drug"] = antiviral_choice

        with col2:
            details["Antiviral_Dose_mg_per_kg"] = st.number_input(
                "Dose, mg/kg",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                key="antiviral_dose_mg_per_kg",
                disabled=antiviral_choice == "Not used",
            )

        if antiviral_choice == "Other":
            details["Antiviral_Other"] = st.text_input(
                "Specify other antiviral",
                key="antiviral_other",
            )
        else:
            details["Antiviral_Other"] = ""

    return details


def render_timed_row(label: str, key: str) -> dict:
    show_main_day_time = key != "analgesia"

    with st.container(border=True):
        if show_main_day_time:
            col1, col2, col3, col4 = st.columns([1.6, 1.4, 1.2, 1.1])
        else:
            col1, col2 = st.columns([1.6, 1.4])

        with col1:
            st.markdown(f"### {label}")

        with col2:
            performed_yn = yes_no_button("Performed", key=f"{key}_performed")

        performed_yes = performed_yn == "Yes"

        if show_main_day_time:
            with col3:
                event_day = st.number_input(
                    "Day",
                    min_value=0,
                    max_value=365,
                    step=1,
                    key=f"{key}_day",
                    disabled=not performed_yes,
                    label_visibility="collapsed",
                    help="Day 0 = day of admission. Day 1 = next day.",
                )

            with col4:
                event_time = st.time_input(
                    "Time",
                    key=f"{key}_time",
                    disabled=not performed_yes,
                    label_visibility="collapsed",
                )
        else:
            event_day = None
            event_time = None

        details = empty_treatment_details(key)

        if performed_yes and key in {
            "analgesia", "steroids", "antibiotics", "respiratory_referral",
            "cxr", "bloods", "cultures", "antivirals",
        }:
            st.divider()
            details = render_treatment_details(key)

    if not performed_yes:
        return {
            "label": label,
            "performed": performed_yn,
            "day": None,
            "time": None,
            "details": details,
        }

    return {
        "label": label,
        "performed": performed_yn,
        "day": event_day,
        "time": event_time,
        "details": details,
    }



def render_timed_section(section_name: str, items: list) -> dict:
    st.header(section_name)
    values = {}

    if section_name == "Treatment":
        left_keys = {"analgesia", "steroids", "antibiotics"}
        left_items = [item for item in items if item["key"] in left_keys]
        right_items = [item for item in items if item["key"] not in left_keys]

        col_left, col_right = st.columns(2)

        with col_left:
            for item in left_items:
                values[item["key"]] = render_timed_row(item["label"], item["key"])

        with col_right:
            for item in right_items:
                values[item["key"]] = render_timed_row(item["label"], item["key"])

        return values

    col_left, col_right = st.columns(2)

    for idx, item in enumerate(items):
        label = item["label"]
        key = item["key"]
        target_col = col_left if idx % 2 == 0 else col_right

        with target_col:
            values[key] = render_timed_row(label, key)

    return values




def render_microbiology_section() -> dict:
    st.header("Microbiology")
    values = {}

    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            values["bacterium_isolated"] = yes_no_button(
                "Bacterium isolated",
                key="bacterium_isolated",
            )

        bacterium_yes = values["bacterium_isolated"] == "Yes"

        with col2:
            values["bacterium"] = st.selectbox(
                "Bacterium",
                options=BACTERIA_OPTIONS,
                key="bacterium",
                disabled=not bacterium_yes,
            )

        if bacterium_yes and values["bacterium"] == "Other":
            values["bacterium_other"] = st.text_input(
                "Specify other bacterium",
                key="bacterium_other",
            )
        else:
            values["bacterium_other"] = ""

    return values


def render_outcome_section() -> dict:
    st.header("Outcome")
    values = {}

    with st.container(border=True):
        st.markdown("### Admission outcome")

        values["highest_respiratory_support"] = st.selectbox(
            "Highest Level of Respiratory Support Required",
            options=RESPIRATORY_SUPPORT_OPTIONS,
            key="highest_respiratory_support",
        )

        ocol1, ocol2, ocol3, ocol4 = st.columns(4)

        with ocol1:
            values["picu_admission"] = yes_no_button(
                "PICU Admission",
                key="picu_admission",
            )

        with ocol2:
            values["developed_atelectasis"] = yes_no_button(
                "Developed Atelectasis",
                key="developed_atelectasis",
            )

        with ocol3:
            values["death"] = yes_no_button(
                "Death",
                key="death",
            )

        with ocol4:
            values["readmitted"] = yes_no_button(
                "Readmitted",
                key="readmitted",
            )

        if values["readmitted"] == "Yes":
            st.markdown("**Readmission details**")

            rcol1, rcol2 = st.columns(2)

            with rcol1:
                values["weeks_to_readmission"] = st.number_input(
                    "Time from discharge to readmission, weeks",
                    min_value=0.0,
                    max_value=104.0,
                    step=0.5,
                    key="weeks_to_readmission",
                )

            with rcol2:
                values["readmission_reason"] = st.selectbox(
                    "Reason for readmission",
                    options=READMISSION_REASON_OPTIONS,
                    key="readmission_reason",
                )

            if values["readmission_reason"] == "Other":
                values["readmission_reason_other"] = st.text_input(
                    "Specify other readmission reason",
                    key="readmission_reason_other",
                )
            else:
                values["readmission_reason_other"] = ""

            values["readmission_notes"] = st.text_area(
                "Readmission notes",
                key="readmission_notes",
                height=80,
                placeholder="Optional brief note on readmission context.",
            )

        else:
            values["weeks_to_readmission"] = ""
            values["readmission_reason"] = ""
            values["readmission_reason_other"] = ""
            values["readmission_notes"] = ""

    return values



def render_saved_data_section() -> None:
    with st.expander("Saved Audit Data"):
        try:
            data = load_sheet_data()
            existing_df = pd.DataFrame(data)

            if not existing_df.empty:
                st.caption(f"{len(existing_df)} records saved")
                st.dataframe(existing_df, use_container_width=True)
                st.download_button(
                    label="Download Data as CSV",
                    data=existing_df.to_csv(index=False).encode("utf-8"),
                    file_name="acs_audit_data.csv",
                    mime="text/csv",
                )
            else:
                st.info("No audit data saved yet.")

        except Exception as e:
            st.warning(f"Could not load saved data from Google Sheets: {e}")


# =========================
# Record builder
# =========================
def build_record(
    patient_id: str,
    admission_month: str,
    admission_year: int,
    admission_time,
    discharge_day: int,
    discharge_time,
    background_values: dict,
    timed_sections: dict,
    microbiology_values: dict,
    outcome_values: dict,
    admission_obs_values: dict,
) -> dict:
    los_hours, los_days = calculate_length_of_stay(
        admission_time,
        discharge_day,
        discharge_time,
    )

    record = {
        "Patient_ID": patient_id.strip(),
        "Admission_Month": admission_month,
        "Admission_Year": admission_year,
        "Admission_Time": admission_time,
        "Discharge_Day": discharge_day,
        "Discharge_Time": discharge_time,
        "Length_of_Stay_hours": los_hours,
        "Length_of_Stay_days": los_days,
    }

    record.update(background_values)
    for field in BACKGROUND_YN_FIELDS:
        record[field] = yn_to_bool(record.get(field))

    record.update(admission_obs_values)
    record["four_hourly_obs_performed"] = yn_to_bool(record.get("four_hourly_obs_performed"))

    for _, items in timed_sections.items():
        for _, values in items.items():
            label = values["label"]
            safe_label = label.replace(" ", "_").replace("/", "_")
            performed_bool = yn_to_bool(values.get("performed"))

            if performed_bool is not True:
                record[f"{safe_label}_Performed"] = performed_bool
                record[f"{safe_label}_Day"] = None
                record[f"{safe_label}_Time"] = None
                record[f"{safe_label}_Time_hrs"] = None

            else:
                hours = calculate_hours_from_admission(
                    admission_time,
                    values["day"],
                    values["time"],
                )

                record[f"{safe_label}_Performed"] = True
                record[f"{safe_label}_Day"] = values["day"]
                record[f"{safe_label}_Time"] = values["time"]
                record[f"{safe_label}_Time_hrs"] = hours

            for detail_key, detail_value in values.get("details", {}).items():
                if detail_key == "Analgesia_Entries":
                    continue
                elif detail_key == "CXR_Changes":
                    record[detail_key] = yn_to_bool(detail_value)
                elif isinstance(detail_value, list):
                    record[detail_key] = serialise_multiselect(detail_value)
                else:
                    record[detail_key] = detail_value

            if label == "Analgesia":
                raw_entries = values.get("details", {}).get("Analgesia_Entries", [])
                used_drugs = []
                used_hrs = []

                for i in range(1, MAX_ANALGESIA_ENTRIES + 1):
                    if i <= len(raw_entries):
                        entry = raw_entries[i - 1]
                        drug = entry.get("drug", "Not used")
                        dose = entry.get("dose", "")
                        dose_unit = entry.get("dose_unit", "")
                        other = entry.get("other", "")
                        day_val = entry.get("day")
                        time_val = entry.get("time")

                        if isinstance(day_val, int) and isinstance(time_val, time):
                            hrs = calculate_hours_from_admission(admission_time, day_val, time_val)
                        else:
                            hrs = None

                        record[f"Analgesia_{i}_Drug"] = drug
                        record[f"Analgesia_{i}_Dose"] = dose
                        record[f"Analgesia_{i}_Dose_Unit"] = dose_unit
                        record[f"Analgesia_{i}_Other"] = other
                        record[f"Analgesia_{i}_Day"] = day_val
                        record[f"Analgesia_{i}_Time"] = time_val
                        record[f"Analgesia_{i}_Time_hrs"] = hrs

                        if drug and drug != "Not used":
                            used_drugs.append(drug)
                            if hrs is not None:
                                used_hrs.append(hrs)
                    else:
                        record[f"Analgesia_{i}_Drug"] = ""
                        record[f"Analgesia_{i}_Dose"] = ""
                        record[f"Analgesia_{i}_Dose_Unit"] = ""
                        record[f"Analgesia_{i}_Other"] = ""
                        record[f"Analgesia_{i}_Day"] = None
                        record[f"Analgesia_{i}_Time"] = None
                        record[f"Analgesia_{i}_Time_hrs"] = None

                record["Analgesia_Entry_Count"] = len(used_drugs)
                record["Analgesia_Drugs_Used"] = "; ".join(used_drugs)
                record["Analgesia_Time_to_First_hrs"] = min(used_hrs) if used_hrs else None

    record.update(microbiology_values)
    record["bacterium_isolated"] = yn_to_bool(record.get("bacterium_isolated"))

    record.update(outcome_values)
    for field in ["picu_admission", "developed_atelectasis", "death", "readmitted"]:
        record[field] = yn_to_bool(record.get(field))

    return record


# =========================
# Save function
# =========================
def normalise_value_for_sheet(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="minutes")

    if isinstance(value, time):
        return value.isoformat(timespec="minutes")

    if value is None:
        return ""

    return value


def save_to_google_sheets(data_dict) -> str:
    """Save a record. If a row already exists for this Patient_ID, update it in
    place instead of appending a duplicate. Returns 'created' or 'updated'."""
    ws = get_sheet()
    headers = ws.row_values(1)

    if not headers:
        headers = ["timestamp", "last_updated"] + list(data_dict.keys())
        ws.append_row(headers)
    else:
        missing_headers = [key for key in data_dict.keys() if key not in headers]

        if "timestamp" not in headers:
            missing_headers = ["timestamp"] + missing_headers

        if "last_updated" not in headers:
            missing_headers = missing_headers + ["last_updated"]

        if missing_headers:
            headers = headers + missing_headers
            ws.update("1:1", [headers])

    now_str = datetime.now().isoformat(sep=" ", timespec="minutes")
    patient_id = str(data_dict.get("Patient_ID", "")).strip()

    existing_row_idx = None
    existing_row_values = None

    if patient_id and "Patient_ID" in headers:
        col_idx = headers.index("Patient_ID") + 1
        col_values = ws.col_values(col_idx)

        for i, val in enumerate(col_values[1:], start=2):
            if val.strip() == patient_id:
                existing_row_idx = i
                break

    if existing_row_idx:
        existing_row_values = ws.row_values(existing_row_idx)
        existing_row_values += [""] * (len(headers) - len(existing_row_values))

    row = []
    for idx, h in enumerate(headers):
        if h == "timestamp":
            if existing_row_values and existing_row_values[idx]:
                row.append(existing_row_values[idx])
            else:
                row.append(now_str)
        elif h == "last_updated":
            row.append(now_str)
        else:
            row.append(normalise_value_for_sheet(data_dict.get(h, "")))

    if existing_row_idx:
        start_a1 = gspread.utils.rowcol_to_a1(existing_row_idx, 1)
        end_a1 = gspread.utils.rowcol_to_a1(existing_row_idx, len(headers))
        ws.update(f"{start_a1}:{end_a1}", [row])
        return "updated"

    ws.append_row(row)
    return "created"


# =========================
# Main app
# =========================
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    if not check_password():
        st.stop()

    initialise_state()
    handle_pending_reset()
    handle_new_record_request()
    render_header()

    (
        patient_id,
        admission_month,
        admission_year,
        admission_time,
        discharge_day,
        discharge_time,
    ) = render_patient_section()

    admission_obs_values = render_admission_observations_section()

    background_values = render_background_section()

    timed_section_values = {}
    for section_name, items in SECTIONS.items():
        timed_section_values[section_name] = render_timed_section(section_name, items)

    microbiology_values = render_microbiology_section()
    outcome_values = render_outcome_section()

    if st.button("Submit Record"):
        if not patient_id.strip():
            st.error("Please enter a Research ID.")

        else:
            los_hours, _ = calculate_length_of_stay(
                admission_time,
                discharge_day,
                discharge_time,
            )

            if los_hours is None:
                st.error("Please enter discharge day and discharge time.")

            elif los_hours < 0:
                st.error("Discharge time cannot be before registration time.")

            else:
                record = build_record(
                    patient_id,
                    admission_month,
                    admission_year,
                    admission_time,
                    discharge_day,
                    discharge_time,
                    background_values,
                    timed_section_values,
                    microbiology_values,
                    outcome_values,
                    admission_obs_values,
                )

                try:
                    action = save_to_google_sheets(record)
                    load_sheet_data.clear()

                    st.session_state["submitted"] = True
                    st.session_state["last_save_action"] = action
                    st.session_state["reset_requested"] = True
                    st.session_state["load_message"] = None

                    st.rerun()

                except Exception as e:
                    st.error(f"Google Sheets save failed: {e}")

    render_saved_data_section()


if __name__ == "__main__":
    main()