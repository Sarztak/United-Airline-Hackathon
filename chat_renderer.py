import streamlit as st
import time

def render_left_bubble_with_progress(content, delay=0.5):
    if content:
        bar = st.progress(0)
        steps = 100
        for i in range(steps):
            time.sleep(delay / steps)
            bar.progress(i + 1)
        bar.empty()
        st.markdown(
            f"""
            <div style='
                background-color:#f9f9f9;
                color:#000000;
                padding:10px;
                border-radius:5px;
                margin-bottom:5px;
                font-size:16px;
            '>
            {content}
            </div>
            """,
            unsafe_allow_html=True
        )

def render_right_bubble_with_progress(content, delay=0.5):
    if content:
        bar = st.progress(0)
        steps = 100
        for i in range(steps):
            time.sleep(delay / steps)
            bar.progress(i + 1)
        bar.empty()
        st.markdown(
            f"""
            <div style='
                background-color:#d6eaff;
                color:#000000;
                padding:10px;
                border-radius:5px;
                margin-bottom:5px;
                font-size:16px;
                text-align:right;
            '>
            {content}
            </div>
            """,
            unsafe_allow_html=True
        )

def render_step_with_progress(step, delay=0.5):
    cols = st.columns([3, 1, 3])
    with cols[0]:
        render_left_bubble_with_progress(step.get("Thought", ""), delay)
        render_left_bubble_with_progress(step.get("Observation", ""), delay)
    with cols[2]:
        render_right_bubble_with_progress(step.get("Action", ""), delay)
    st.markdown("<hr>", unsafe_allow_html=True)
