import streamlit as st
import pandas as pd
from datetime import datetime
import gspread

#To run app put this into terminal : streamlit run app.py


# =========================
# Config
# =========================

APP_TITLE = "Sickle Cell ACS Audit Tool"

SECTIONS = {
    "Investigations": [
        {"label": "Bloods", "key": "bloods"},
        {"label": "CXR", "key": "cxr"},
        {"label": "Cultures", "key": "cultures"},
        {"label": "Group and Hold / Crossmatch", "key": "group_hold_cross"},
        {"label": "ABG", "key": "abg"},
    ],
    "Treatment": [
        {"label": "Oxygen", "key": "oxygen"},
        {"label": "Analgesia", "key": "analgesia"},
        {"label": "Steroids", "key": "steroids"},
        {"label": "Antibiotics", "key": "antibiotics"},
        {"label": "Fluids", "key": "fluids"},
        {"label": "Bronchodilators", "key": "bronchodilators"},
        {"label": "Transfusion", "key": "transfusion"},
        {"label": "Respiratory Physiotherapy", "key": "respiratory_pt"},
    ],
    "Discussions": [
        {"label": "Discussion with Haematology", "key": "haematology_discussion"},
        {"label": "Discussion with ICU", "key": "icu_discussion"},
    ],
}

OUTCOME_FIELDS = [
    {
        "label": "Ventilation Required",
        "key": "ventilation_required",
        "type": "select",
        "options": ["None", "NIV", "Tube"],
    },
    {"label": "PICU Admission", "key": "picu_admission", "type": "checkbox"},
    {"label": "Length of Admission (days)", "key": "length_of_admission", "type": "number"},
    {"label": "Developed Atelectasis", "key": "developed_atelectasis", "type": "checkbox"},
]

ALL_TIMED_ITEMS = [item for section in SECTIONS.values() for item in section]


@st.cache_resource
def get_sheet():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open("ACS Audit")
    return sh.sheet1

ws = get_sheet()

@st.cache_data(ttl=10)
def load_sheet_data():
    return ws.get_all_records()


# =========================
# Reset helpers
# =========================
def reset_form_state() -> None:
    now = datetime.now().replace(second=0, microsecond=0)

    st.session_state["patient_id"] = ""
    st.session_state["admission_datetime"] = now

    for item in ALL_TIMED_ITEMS:
        key = item["key"]
        st.session_state[f"{key}_date"] = now.date()
        st.session_state[f"{key}_time"] = now.time()
        st.session_state[f"{key}_not_done"] = False

    st.session_state["ventilation_required"] = "None"
    st.session_state["picu_admission"] = False
    st.session_state["length_of_admission"] = 0.0
    st.session_state["developed_atelectasis"] = False


def handle_pending_reset() -> None:
    if st.session_state.get("reset_requested", False):
        reset_form_state()
        st.session_state["reset_requested"] = False


# =========================
# Time helpers
# =========================
def combine_date_and_time(selected_date, selected_time):
    if selected_date is None or selected_time is None:
        return None
    return datetime.combine(selected_date, selected_time)


def calculate_hours_from_admission(admission_dt, event_dt):
    if event_dt is None:
        return None
    return round((event_dt - admission_dt).total_seconds() / 3600, 2)


# =========================
# Session state helpers
# =========================
def initialise_state() -> None:
    if "admission_datetime" not in st.session_state:
        now = datetime.now().replace(second=0, microsecond=0)
        st.session_state["admission_datetime"] = now

    if "patient_id" not in st.session_state:
        st.session_state["patient_id"] = ""

    if "reset_requested" not in st.session_state:
        st.session_state["reset_requested"] = False

    for item in ALL_TIMED_ITEMS:
        key = item["key"]
        if f"{key}_date" not in st.session_state:
            st.session_state[f"{key}_date"] = st.session_state["admission_datetime"].date()
        if f"{key}_time" not in st.session_state:
            st.session_state[f"{key}_time"] = st.session_state["admission_datetime"].time()
        if f"{key}_not_done" not in st.session_state:
            st.session_state[f"{key}_not_done"] = False

    for field in OUTCOME_FIELDS:
        key = field["key"]
        if key not in st.session_state:
            if field["type"] == "checkbox":
                st.session_state[key] = False
            elif field["type"] == "number":
                st.session_state[key] = 0.0
            elif field["type"] == "select":
                st.session_state[key] = field["options"][0]


def sync_interventions_to_admission() -> None:
    admission_dt = st.session_state["admission_datetime"]
    admission_date = admission_dt.date()
    admission_time = admission_dt.time()

    for item in ALL_TIMED_ITEMS:
        key = item["key"]
        if not st.session_state.get(f"{key}_not_done", False):
            st.session_state[f"{key}_date"] = admission_date
            st.session_state[f"{key}_time"] = admission_time


# =========================
# UI sections
# =========================
def render_header() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Record timings of key ACS interventions relative to admission time.")
    st.caption("Live saving to Google Sheets.")

    st.markdown(
        """
        <style>
            .block-container {
                max-width: 95%;
                padding-top: 1.25rem;
                padding-bottom: 1.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_patient_section():
    st.header("Patient Information")
    col1, col2 = st.columns(2)

    with col1:
        patient_id = st.text_input("Patient ID", key="patient_id")

    with col2:
        admission_datetime = st.datetime_input(
            "Admission Date & Time",
            key="admission_datetime",
            on_change=sync_interventions_to_admission,
        )

    return patient_id, admission_datetime


def render_timed_row(label: str, key: str) -> dict:
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1.8, 1.2, 1.3, 1.1])

        with col1:
            st.markdown(f"**{label}**")

        with col2:
            not_done = st.checkbox("Not performed", key=f"{key}_not_done")

        with col3:
            event_date = st.date_input(
                "Date",
                key=f"{key}_date",
                disabled=not_done,
                label_visibility="collapsed",
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
            "date": None,
            "time": None,
        }

    return {
        "label": label,
        "performed": True,
        "date": event_date,
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


def render_outcome_section() -> dict:
    st.header("Outcome")
    values = {}
    col1, col2 = st.columns(2)

    with col1:
        values["ventilation_required"] = st.selectbox(
            "Ventilation Required",
            options=["None", "NIV", "Tube"],
            key="ventilation_required",
        )
        values["picu_admission"] = st.checkbox(
            "PICU Admission",
            key="picu_admission",
        )

    with col2:
        values["length_of_admission"] = st.number_input(
            "Length of Admission (days)",
            min_value=0.0,
            step=1.0,
            key="length_of_admission",
        )
        values["developed_atelectasis"] = st.checkbox(
            "Developed Atelectasis",
            key="developed_atelectasis",
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
def build_record(patient_id: str, admission_datetime, timed_sections: dict, outcome_values: dict) -> dict:
    record = {
        "Patient_ID": patient_id.strip(),
        "Admission_Datetime": admission_datetime,
    }

    for _, items in timed_sections.items():
        for _, values in items.items():
            label = values["label"]
            safe_label = label.replace(" ", "_").replace("/", "_")

            if not values.get("performed", True):
                record[f"{safe_label}_Performed"] = False
                record[f"{safe_label}_Datetime"] = None
                record[f"{safe_label}_Time_hrs"] = None
            else:
                event_dt = combine_date_and_time(values["date"], values["time"])
                hours = calculate_hours_from_admission(admission_datetime, event_dt)
                record[f"{safe_label}_Performed"] = True
                record[f"{safe_label}_Datetime"] = event_dt
                record[f"{safe_label}_Time_hrs"] = hours

    for key, value in outcome_values.items():
        record[key] = value

    return record

# =========================
# Save Function
# =========================

def save_to_google_sheets(data_dict):
    headers = ws.row_values(1)

    if not headers:
        raise ValueError("Google Sheet has no header row.")

    row = []
    for h in headers:
        if h == "timestamp":
            row.append(datetime.now().isoformat())
        else:
            value = data_dict.get(h, "")

            if isinstance(value, datetime):
                value = value.isoformat(sep=" ", timespec="minutes")
            elif value is None:
                value = ""

            row.append(value)

    ws.append_row(row)
# =========================
# Main app
# =========================
def main() -> None:
    initialise_state()
    handle_pending_reset()
    render_header()

    patient_id, admission_datetime = render_patient_section()

    timed_section_values = {}
    for section_name, items in SECTIONS.items():
        timed_section_values[section_name] = render_timed_section(section_name, items)

    outcome_values = render_outcome_section()

    if st.button("Submit Record"):
        if not patient_id.strip():
            st.error("Please enter a Patient ID.")
        else:
            record = build_record(
                patient_id,
                admission_datetime,
                timed_section_values,
                outcome_values,
            )
            try:
                save_to_google_sheets(record)
                load_sheet_data.clear()
                st.session_state["reset_requested"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Google Sheets save failed: {e}")

    render_saved_data_section()

if __name__ == "__main__":
    main()