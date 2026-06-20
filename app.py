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

STEROID_OPTIONS = [
    "Dexamethasone",
    "Hydrocortisone",
    "Prednisolone",
    "Methylprednisolone",
    "Other",
]

ANTIBIOTIC_OPTIONS = [
    "Co-amoxiclav",
    "Ceftriaxone",
    "Cefotaxime",
    "Piperacillin-tazobactam / Tazocin",
    "Clarithromycin",
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

SECTIONS = {
    "Investigations": [
        {"label": "Bloods", "key": "bloods"},
        {"label": "CXR", "key": "cxr"},
        {"label": "Cultures", "key": "cultures"},
        {"label": "Group and Hold / Crossmatch", "key": "group_hold_cross"},
        {"label": "VBG", "key": "vbg"},
    ],
    "Treatment": [
        {"label": "Oxygen", "key": "oxygen"},
        {"label": "Analgesia", "key": "analgesia"},
        {"label": "Steroids", "key": "steroids"},
        {"label": "Antibiotics", "key": "antibiotics"},
        {"label": "Fluids", "key": "fluids"},
        {"label": "Bronchodilators", "key": "bronchodilators"},
        {"label": "Simple Transfusion", "key": "simple_transfusion"},
        {"label": "Exchange Transfusion", "key": "exchange_transfusion"},
        {"label": "Respiratory Physiotherapy", "key": "respiratory_pt"},
    ],
    "Discussions": [
        {"label": "Discussion with Haematology", "key": "haematology_discussion"},
        {"label": "Discussion with ICU", "key": "icu_discussion"},
    ],
}

ALL_TIMED_ITEMS = [item for section in SECTIONS.values() for item in section]


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


# =========================
# Reset helpers
# =========================
def reset_form_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    st.session_state["patient_id"] = ""

    st.session_state["admission_month"] = MONTH_OPTIONS[now.month - 1]
    st.session_state["admission_year"] = now.year
    st.session_state["admission_time"] = now.time()

    st.session_state["discharge_day"] = 0
    st.session_state["discharge_time"] = now.time()

    st.session_state["age_at_admission"] = 0
    st.session_state["sex"] = "Unknown"
    st.session_state["genotype"] = "Unknown"
    st.session_state["genotype_other"] = ""

    st.session_state["influenza_vaccinated"] = False
    st.session_state["pneumococcal_vaccinated"] = False
    st.session_state["hib_vaccinated"] = False

    st.session_state["splenectomy"] = False
    st.session_state["liver_transplant"] = False
    st.session_state["bone_marrow_transplant"] = False

    st.session_state["hydroxyurea"] = False
    st.session_state["folic_acid"] = False
    st.session_state["vitamin_d"] = False
    st.session_state["regular_transfusion_programme"] = False
    st.session_state["regular_venesection"] = False
    st.session_state["regular_exchange_transfusion_programme"] = False
    st.session_state["background_notes"] = ""

    for item in ALL_TIMED_ITEMS:
        key = item["key"]
        st.session_state[f"{key}_day"] = 0
        st.session_state[f"{key}_time"] = now.time()
        st.session_state[f"{key}_not_done"] = False

    st.session_state["steroids_given"] = []
    st.session_state["steroids_other"] = ""
    st.session_state["antibiotics_given"] = []
    st.session_state["antibiotics_other"] = ""

    st.session_state["highest_respiratory_support"] = "None"
    st.session_state["bacterium_isolated"] = False
    st.session_state["bacterium"] = "None isolated"
    st.session_state["bacterium_other"] = ""

    st.session_state["picu_admission"] = False
    st.session_state["developed_atelectasis"] = False
    st.session_state["death"] = False


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
# Session state helpers
# =========================
def initialise_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    defaults = {
        "patient_id": "",
        "reset_requested": False,

        "admission_month": MONTH_OPTIONS[now.month - 1],
        "admission_year": now.year,
        "admission_time": now.time(),
        "discharge_day": 0,
        "discharge_time": now.time(),

        "age_at_admission": 0,
        "sex": "Unknown",
        "genotype": "Unknown",
        "genotype_other": "",

        "influenza_vaccinated": False,
        "pneumococcal_vaccinated": False,
        "hib_vaccinated": False,

        "splenectomy": False,
        "liver_transplant": False,
        "bone_marrow_transplant": False,

        "hydroxyurea": False,
        "folic_acid": False,
        "vitamin_d": False,
        "regular_transfusion_programme": False,
        "regular_venesection": False,
        "regular_exchange_transfusion_programme": False,
        "background_notes": "",

        "steroids_given": [],
        "steroids_other": "",
        "antibiotics_given": [],
        "antibiotics_other": "",

        "highest_respiratory_support": "None",
        "bacterium_isolated": False,
        "bacterium": "None isolated",
        "bacterium_other": "",

        "picu_admission": False,
        "developed_atelectasis": False,
        "death": False,
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

        if f"{key}_not_done" not in st.session_state:
            st.session_state[f"{key}_not_done"] = False


def sync_interventions_to_admission() -> None:
    admission_time = st.session_state["admission_time"]

    for item in ALL_TIMED_ITEMS:
        key = item["key"]

        if not st.session_state.get(f"{key}_not_done", False):
            st.session_state[f"{key}_day"] = 0
            st.session_state[f"{key}_time"] = admission_time


# =========================
# UI sections
# =========================
def render_header() -> None:
    st.title(APP_TITLE)
    st.caption("Record timings of key ACS interventions relative to admission time.")
    st.caption("No specific admission, discharge or intervention dates are collected.")

    if st.session_state.get("submitted"):
        st.success("✅ Submitted successfully")
        st.session_state["submitted"] = False

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_patient_section():
    st.header("Patient Information")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        patient_id = st.text_input("Research ID", key="patient_id")

    with col2:
        admission_month = st.selectbox(
            "Admission Month",
            options=MONTH_OPTIONS,
            key="admission_month",
        )

    with col3:
        admission_year = st.selectbox(
            "Admission Year",
            options=YEAR_OPTIONS,
            key="admission_year",
        )

    with col4:
        admission_time = st.time_input(
            "Admission Time",
            key="admission_time",
            on_change=sync_interventions_to_admission,
        )

    st.subheader("Discharge")

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


def render_background_section() -> dict:
    st.header("Patient Phenotype")
    values = {}

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

    st.subheader("Vaccination Status")
    vacc_col1, vacc_col2, vacc_col3 = st.columns(3)

    with vacc_col1:
        values["influenza_vaccinated"] = st.checkbox(
            "Influenza vaccinated",
            key="influenza_vaccinated",
        )

    with vacc_col2:
        values["pneumococcal_vaccinated"] = st.checkbox(
            "Pneumococcal vaccinated",
            key="pneumococcal_vaccinated",
        )

    with vacc_col3:
        values["hib_vaccinated"] = st.checkbox(
            "Haemophilus influenzae type B vaccinated",
            key="hib_vaccinated",
        )

    st.subheader("Relevant Background History")
    hist_col1, hist_col2, hist_col3 = st.columns(3)

    with hist_col1:
        values["splenectomy"] = st.checkbox(
            "Splenectomy",
            key="splenectomy",
        )

    with hist_col2:
        values["liver_transplant"] = st.checkbox(
            "Liver transplant",
            key="liver_transplant",
        )

    with hist_col3:
        values["bone_marrow_transplant"] = st.checkbox(
            "Bone marrow transplant",
            key="bone_marrow_transplant",
        )

    st.subheader("Background Medications / Programmes")
    med_col1, med_col2, med_col3 = st.columns(3)

    with med_col1:
        values["hydroxyurea"] = st.checkbox("Hydroxyurea", key="hydroxyurea")
        values["folic_acid"] = st.checkbox("Folic acid", key="folic_acid")

    with med_col2:
        values["vitamin_d"] = st.checkbox("Vitamin D", key="vitamin_d")
        values["regular_transfusion_programme"] = st.checkbox(
            "Regular transfusion programme",
            key="regular_transfusion_programme",
        )

    with med_col3:
        values["regular_venesection"] = st.checkbox(
            "Regular venesection",
            key="regular_venesection",
        )
        values["regular_exchange_transfusion_programme"] = st.checkbox(
            "Regular exchange transfusion programme",
            key="regular_exchange_transfusion_programme",
        )

    values["background_notes"] = st.text_area(
        "Other background notes",
        key="background_notes",
        height=80,
    )

    return values


def render_timed_row(label: str, key: str) -> dict:
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1.8, 1.2, 1.3, 1.1])

        with col1:
            st.markdown(f"**{label}**")

        with col2:
            not_done = st.checkbox("Not performed", key=f"{key}_not_done")

        with col3:
            event_day = st.number_input(
                "Day",
                min_value=0,
                max_value=365,
                step=1,
                key=f"{key}_day",
                disabled=not_done,
                label_visibility="collapsed",
                help="Day 0 = day of admission. Day 1 = next day.",
            )

        with col4:
            event_time = st.time_input(
                "Time",
                key=f"{key}_time",
                disabled=not_done,
                label_visibility="collapsed",
            )

    if not_done:
        return {
            "label": label,
            "performed": False,
            "day": None,
            "time": None,
        }

    return {
        "label": label,
        "performed": True,
        "day": event_day,
        "time": event_time,
    }


def render_timed_section(section_name: str, items: list) -> dict:
    st.header(section_name)
    values = {}
    col_left, col_right = st.columns(2)

    for idx, item in enumerate(items):
        label = item["label"]
        key = item["key"]
        target_col = col_left if idx % 2 == 0 else col_right

        with target_col:
            values[key] = render_timed_row(label, key)

    return values


def render_drug_details_section() -> dict:
    st.header("Drug Details")
    values = {}

    col1, col2 = st.columns(2)

    with col1:
        values["steroids_given"] = st.multiselect(
            "Steroids given",
            options=STEROID_OPTIONS,
            key="steroids_given",
        )

        if "Other" in values["steroids_given"]:
            values["steroids_other"] = st.text_input(
                "Specify other steroid",
                key="steroids_other",
            )
        else:
            values["steroids_other"] = ""

    with col2:
        values["antibiotics_given"] = st.multiselect(
            "Antibiotics given",
            options=ANTIBIOTIC_OPTIONS,
            key="antibiotics_given",
        )

        if "Other" in values["antibiotics_given"]:
            values["antibiotics_other"] = st.text_input(
                "Specify other antibiotic",
                key="antibiotics_other",
            )
        else:
            values["antibiotics_other"] = ""

    return values


def render_microbiology_section() -> dict:
    st.header("Microbiology")
    values = {}

    col1, col2 = st.columns(2)

    with col1:
        values["bacterium_isolated"] = st.checkbox(
            "Bacterium isolated",
            key="bacterium_isolated",
        )

    with col2:
        values["bacterium"] = st.selectbox(
            "Bacterium",
            options=BACTERIA_OPTIONS,
            key="bacterium",
            disabled=not values["bacterium_isolated"],
        )

    if values["bacterium_isolated"] and values["bacterium"] == "Other":
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
    col1, col2 = st.columns(2)

    with col1:
        values["highest_respiratory_support"] = st.selectbox(
            "Highest Level of Respiratory Support Required",
            options=RESPIRATORY_SUPPORT_OPTIONS,
            key="highest_respiratory_support",
        )

        values["picu_admission"] = st.checkbox(
            "PICU Admission",
            key="picu_admission",
        )

    with col2:
        values["developed_atelectasis"] = st.checkbox(
            "Developed Atelectasis",
            key="developed_atelectasis",
        )

        values["death"] = st.checkbox(
            "Death",
            key="death",
        )

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
    drug_values: dict,
    microbiology_values: dict,
    outcome_values: dict,
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

    for _, items in timed_sections.items():
        for _, values in items.items():
            label = values["label"]
            safe_label = label.replace(" ", "_").replace("/", "_")

            if not values.get("performed", True):
                record[f"{safe_label}_Performed"] = False
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

    record["Steroids_given"] = serialise_multiselect(
        drug_values.get("steroids_given", [])
    )
    record["Steroids_other"] = drug_values.get("steroids_other", "")

    record["Antibiotics_given"] = serialise_multiselect(
        drug_values.get("antibiotics_given", [])
    )
    record["Antibiotics_other"] = drug_values.get("antibiotics_other", "")

    record.update(microbiology_values)
    record.update(outcome_values)

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


def save_to_google_sheets(data_dict):
    ws = get_sheet()
    headers = ws.row_values(1)

    if not headers:
        headers = ["timestamp"] + list(data_dict.keys())
        ws.append_row(headers)

    else:
        missing_headers = [key for key in data_dict.keys() if key not in headers]

        if "timestamp" not in headers:
            missing_headers = ["timestamp"] + missing_headers

        if missing_headers:
            headers = headers + missing_headers
            ws.update("1:1", [headers])

    row = []

    for h in headers:
        if h == "timestamp":
            row.append(datetime.now().isoformat(sep=" ", timespec="minutes"))
        else:
            row.append(normalise_value_for_sheet(data_dict.get(h, "")))

    ws.append_row(row)


# =========================
# Main app
# =========================
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    if not check_password():
        st.stop()

    initialise_state()
    handle_pending_reset()
    render_header()

    (
        patient_id,
        admission_month,
        admission_year,
        admission_time,
        discharge_day,
        discharge_time,
    ) = render_patient_section()

    background_values = render_background_section()

    timed_section_values = {}
    for section_name, items in SECTIONS.items():
        timed_section_values[section_name] = render_timed_section(section_name, items)

    drug_values = render_drug_details_section()
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
                st.error("Discharge time cannot be before admission time.")

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
                    drug_values,
                    microbiology_values,
                    outcome_values,
                )

                try:
                    save_to_google_sheets(record)
                    load_sheet_data.clear()

                    st.session_state["submitted"] = True
                    st.session_state["reset_requested"] = True

                    st.rerun()

                except Exception as e:
                    st.error(f"Google Sheets save failed: {e}")

    render_saved_data_section()


if __name__ == "__main__":
    main()
