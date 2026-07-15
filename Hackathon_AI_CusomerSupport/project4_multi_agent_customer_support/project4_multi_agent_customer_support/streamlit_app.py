"""Entry point: `streamlit run streamlit_app.py`.

Just routes to one of the two views (Section 8). All the actual logic —
graphs, agents, tools, storage — lives in the modules those views import.
"""
import streamlit as st

from views import approver_queue, customer_chat

st.set_page_config(page_title="Multi-Agent Support POC", layout="wide")

view = st.sidebar.radio("View", ["Customer Chat", "Approver Queue"])

st.sidebar.divider()

if view == "Customer Chat":
    customer_chat.render()
else:
    approver_queue.render()
