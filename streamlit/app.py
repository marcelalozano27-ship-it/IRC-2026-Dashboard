import streamlit as st
import pandas as pd

st.set_page_config(page_title="IRC 2026 Dashboard", layout="wide")

st.title("IRC 2026 Participation Dashboard")

activities = pd.read_csv("data/activity_level.csv")
public = pd.read_csv("data/public_signups.csv")
volunteers = pd.read_csv("data/volunteer_signups.csv")

st.subheader("Activity Data Preview")
st.dataframe(activities.head())

st.subheader("Key Metrics")

col1, col2, col3 = st.columns(3)

col1.metric("Total Activities", len(activities))
col2.metric("Total Visitors", int(activities["TotalVisitors"].sum()))
col3.metric("Volunteer Hours", round(activities["VolunteerHours"].sum(), 1))

st.subheader("Visitors by Activity Type")

visitors_by_type = (
    activities.groupby("ActivityType")["TotalVisitors"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(visitors_by_type)

st.subheader("Volunteer Hours by Activity Type")

volunteer_hours = (
    activities.groupby("ActivityType")["VolunteerHours"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(volunteer_hours)
