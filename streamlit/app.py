import streamlit as st
import pandas as pd

st.set_page_config(page_title="IRC 2026 Dashboard", layout="wide")

st.title("IRC 2026 Participation Dashboard")

activities = pd.read_csv("data/activity_level.csv")
public = pd.read_csv("data/public_signups.csv")
volunteers = pd.read_csv("data/volunteer_signups.csv")

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")

st.sidebar.header("Filters")

activity_options = sorted(activities["ActivityType"].dropna().unique())

selected_activity = st.sidebar.multiselect(
    "Activity Type",
    activity_options,
    default=activity_options
)

min_visitors = int(activities["TotalVisitors"].min())
max_visitors = int(activities["TotalVisitors"].max())

visitor_range = st.sidebar.slider(
    "Total Visitors",
    min_value=min_visitors,
    max_value=max_visitors,
    value=(min_visitors, max_visitors)
)

filtered = activities[
    (activities["ActivityType"].isin(selected_activity)) &
    (activities["TotalVisitors"].between(visitor_range[0], visitor_range[1]))
]

st.subheader("Filtered Activity Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Activities", len(filtered))
col2.metric("Total Visitors", int(filtered["TotalVisitors"].sum()))
col3.metric("Volunteer Hours", round(filtered["VolunteerHours"].sum(), 1))

st.subheader("Visitors by Activity Type")

visitors_by_type = (
    filtered.groupby("ActivityType")["TotalVisitors"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(visitors_by_type)

st.subheader("Volunteer Hours by Activity Type")

volunteer_hours = (
    filtered.groupby("ActivityType")["VolunteerHours"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(volunteer_hours)

st.subheader("Filtered Activity Data")
st.dataframe(filtered)
