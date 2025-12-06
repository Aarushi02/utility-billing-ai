import streamlit as st
from src.database.db_utils import (
    get_distinct_sc_codes,
    get_versions_for_sc,
    get_logic_for_sc_version,
)

st.set_page_config(page_title="Tariff Logic Viewer", page_icon="📑", layout="wide")


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
    st.title("📑 Utility Tariff Logic Viewer (DB Mode)")

    # 1️⃣ LOAD SC CODES FROM DB
    sc_codes = get_distinct_sc_codes()
    if not sc_codes:
        st.error("No SC codes available in the database.")
        return

    selected_sc = st.selectbox("Select Service Classification:", sc_codes)
    st.markdown("---")

    # 2️⃣ LOAD VERSIONS FOR SELECTED SC
    versions = get_versions_for_sc(selected_sc)
    if not versions:
        st.warning("No versions found for this SC code.")
        return

    selected_version = st.selectbox(
        f"Select Effective Date for {selected_sc}:",
        versions
    )
    st.markdown("---")

    # 3️⃣ FETCH LOGIC JSON FROM DB
    logic_json = get_logic_for_sc_version(selected_sc, selected_version)
    if not logic_json:
        st.error("No logic found for this version in the database.")
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
