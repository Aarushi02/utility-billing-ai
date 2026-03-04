import streamlit as st
import requests
import time

from src.utils.config import get_env

st.set_page_config(page_title="Tariff Logic Viewer", page_icon="📑", layout="wide")


API_BASE_URL = get_env("API_BASE_URL", "http://localhost:8000")


@st.cache_data(ttl=60, show_spinner=False)
def _get_api_json(path: str):
    url = f"{API_BASE_URL}{path}"
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise

    if last_exc:
        raise last_exc


# ------------------------------------------
# RENDER SINGLE STEP
# ------------------------------------------
def _render_logic_step(step):
    name = step.get("step_name", "Unknown Step")
    c_type = step.get("charge_type", "N/A")
    condition = step.get("condition", "Always")

    icon = "💰" if c_type == "fixed_fee" else "⚡"
    st.markdown(f"#### {icon} {name}")

    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        st.caption("Charge Type")
        st.markdown(f"**{c_type.replace('_',' ').title()}**")

    with c2:
        st.caption("Logic / Value")
        val = step.get("value")

        if isinstance(val, dict):
            st.markdown("**Rate Table:**")
            for k, v in val.items():
                try:
                    v_fmt = f"${float(v):,.4f}"
                except:
                    v_fmt = str(v)
                st.write(f"- **{k}**: {v_fmt}")

        elif c_type == "fixed_fee":
            st.metric("Amount", f"${float(val):,.2f}", label_visibility="collapsed")

        elif c_type == "per_kwh":
            st.metric("Rate", f"${float(val):.5f}/kWh", label_visibility="collapsed")

        elif c_type == "formula":
            st.code(step.get("python_formula", "N/A"), language="python")

        else:
            st.write(val)

    with c3:
        unit = step.get("unit")
        if unit:
            st.caption("Applied To")
            st.code(unit, language="python")

    if condition != "Always":
        st.info(f"Condition: `{condition}`", icon="⚠️")

    st.divider()


# ------------------------------------------
# MAIN STREAMLIT VIEW
# ------------------------------------------
def render_tariff_details_viewer():
    st.title("📑 Utility Tariff Logic Viewer")

    # 1️⃣ LOAD SC CODES FROM DB
    try:
        sc_codes = _get_api_json("/api/v1/tariffs/sc-codes").get("sc_codes", [])
    except requests.RequestException as exc:
        st.error(f"Unable to load SC codes from API: {exc}")
        return

    if not sc_codes:
        st.error("No SC codes available from API.")
        return

    # ----------------------------------
    # SIDE-BY-SIDE DROPDOWNS
    # ----------------------------------
    col1, col2 = st.columns([1, 1])

    with col1:
        selected_sc = st.selectbox("Service Classification (SC):", sc_codes)

    # 2️⃣ LOAD VERSIONS AFTER SC IS PICKED
    try:
        versions = _get_api_json(f"/api/v1/tariffs/{selected_sc}/versions").get("versions", [])
    except requests.RequestException as exc:
        st.error(f"Unable to load versions from API: {exc}")
        return

    if not versions:
        st.warning("No versions found for this SC code.")
        return

    with col2:
        selected_version = st.selectbox(
            f"Effective Date for {selected_sc}:", 
            versions
        )

    st.markdown("---")

    # 3️⃣ FETCH LOGIC JSON FROM DB
    try:
        logic_json = _get_api_json(
            f"/api/v1/tariffs/{selected_sc}/versions/{selected_version}"
        ).get("logic")
    except requests.RequestException as exc:
        st.error(f"Unable to load tariff logic from API: {exc}")
        return

    if not logic_json:
        st.error("No logic found for this version.")
        return

    # 4️⃣ DISPLAY HEADER INFO
    st.header(f"{selected_sc} — Version {selected_version}")

    desc = logic_json.get("description")
    if desc:
        st.caption(desc)

    # 5️⃣ DISPLAY STEPS
    steps = logic_json.get("logic_steps", [])
    if steps:
        st.subheader("Calculation Logic")
        for step in steps:
            _render_logic_step(step)
    else:
        st.warning("This version has no calculation logic steps.")

    # 6️⃣ RAW JSON VIEWER
    with st.expander("View Raw JSON Logic"):
        st.json(logic_json)


if __name__ == "__main__":
    render_tariff_details_viewer()
