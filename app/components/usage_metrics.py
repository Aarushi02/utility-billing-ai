import os
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


def render():
    st.title("Usage Metrics")

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/metrics/summary", timeout=20)
        response.raise_for_status()
        data = response.json()

        aws = data.get("aws", {})
        llm = data.get("llm", {})

        st.subheader("LLM Usage")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LLM Spend", f"${float(llm.get('month_to_date_spend', 0.0)):.4f}")
        c2.metric("LLM Requests", f"{int(llm.get('requests', 0))}")
        c3.metric("Input Tokens", f"{int(llm.get('input_tokens', 0))}")
        c4.metric("Output Tokens", f"{int(llm.get('output_tokens', 0))}")

        st.subheader("AWS Usage")
        a1, a2, a3 = st.columns(3)
        a1.metric("AWS Requests", f"{int(aws.get('requests', 0))}")
        a2.metric("AWS Success", f"{int(aws.get('success', 0))}")
        a3.metric("AWS Failures", f"{int(aws.get('failures', 0))}")

        with st.expander("LLM Details"):
            st.write("LLM Status:", llm.get("status", "unknown"))
            st.write("LLM Model:", llm.get("model", "unknown"))
            st.write("Total Tokens:", llm.get("total_tokens", 0))
            st.write("By Model:", llm.get("by_model", {}))
            st.write("Recent LLM Calls:", llm.get("recent_calls", []))

        with st.expander("AWS Details"):
            st.write("AWS Status:", aws.get("status", "unknown"))
            st.write("By Operation:", aws.get("by_operation", {}))
            st.write("Recent AWS Calls:", aws.get("recent_calls", []))

    except Exception as e:
        st.error(f"Failed to load usage metrics: {e}")