import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="IRC Activity Planning Dashboard", layout="wide")

st.title("IRC Activity Planning Dashboard")
st.caption("Prototype dashboard for attendance trends, activity planning, and stakeholder recommendations.")

# -----------------------------
# Load Data
# -----------------------------

@st.cache_data
def load_data():
    activities = pd.read_csv("data/activity_level.csv")
    public = pd.read_csv("data/public_signups.csv")
    volunteers = pd.read_csv("data/volunteer_signups.csv")
    return activities, public, volunteers

activities, public, volunteers = load_data()

# -----------------------------
# Basic Cleaning
# -----------------------------

date_col = "Date" if "Date" in activities.columns else None

if date_col:
    activities[date_col] = pd.to_datetime(activities[date_col], errors="coerce")
    activities["Year"] = activities[date_col].dt.year
    activities["Month"] = activities[date_col].dt.month_name()
    activities["MonthNum"] = activities[date_col].dt.month
    activities["DayOfWeek"] = activities[date_col].dt.day_name()

# Add safe numeric columns
for col in ["TotalVisitors", "VolunteerHours", "VisitorsRegistered", "VisitorNoShow", "WalkUp"]:
    if col in activities.columns:
        activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

# Attendance rate if possible
if "VisitorsRegistered" in activities.columns and "VisitorNoShow" in activities.columns:
    activities["ActualVisitors"] = activities["VisitorsRegistered"] - activities["VisitorNoShow"]
    activities["AttendanceRate"] = np.where(
        activities["VisitorsRegistered"] > 0,
        activities["ActualVisitors"] / activities["VisitorsRegistered"],
        np.nan
    )
elif "TotalVisitors" in activities.columns:
    activities["ActualVisitors"] = activities["TotalVisitors"]
    activities["AttendanceRate"] = np.nan

# -----------------------------
# Sidebar Filters
# -----------------------------

st.sidebar.header("Filters")

filtered = activities.copy()

if "ActivityType" in activities.columns:
    activity_types = sorted(activities["ActivityType"].dropna().unique())
    selected_types = st.sidebar.multiselect(
        "Activity Type",
        activity_types,
        default=activity_types
    )
    filtered = filtered[filtered["ActivityType"].isin(selected_types)]

if "Year" in activities.columns and activities["Year"].notna().any():
    years = sorted(activities["Year"].dropna().unique().astype(int))
    selected_years = st.sidebar.multiselect(
        "Year",
        years,
        default=years
    )
    filtered = filtered[filtered["Year"].isin(selected_years)]

if "Month" in activities.columns:
    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    available_months = [m for m in month_order if m in activities["Month"].dropna().unique()]
    selected_months = st.sidebar.multiselect(
        "Month",
        available_months,
        default=available_months
    )
    filtered = filtered[filtered["Month"].isin(selected_months)]

if "TotalVisitors" in activities.columns:
    min_visitors = int(activities["TotalVisitors"].min())
    max_visitors = int(activities["TotalVisitors"].max())

    visitor_range = st.sidebar.slider(
        "Total Visitors Range",
        min_value=min_visitors,
        max_value=max_visitors,
        value=(min_visitors, max_visitors)
    )

    filtered = filtered[
        filtered["TotalVisitors"].between(visitor_range[0], visitor_range[1])
    ]

# -----------------------------
# Tabs
# -----------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Activity Performance",
    "Monthly Recommendations",
    "Attendance & No-Shows",
    "Raw Data"
])

# -----------------------------
# Tab 1: Overview
# -----------------------------

with tab1:
    st.subheader("Dashboard Overview")

    col1, col2, col3, col4 = st.columns(4)

    total_activities = len(filtered)
    total_visitors = filtered["TotalVisitors"].sum() if "TotalVisitors" in filtered.columns else 0
    volunteer_hours = filtered["VolunteerHours"].sum() if "VolunteerHours" in filtered.columns else 0
    avg_attendance = filtered["AttendanceRate"].mean() if "AttendanceRate" in filtered.columns else np.nan

    col1.metric("Activities", f"{total_activities:,}")
    col2.metric("Total Visitors", f"{int(total_visitors):,}")
    col3.metric("Volunteer Hours", f"{round(volunteer_hours, 1):,}")
    col4.metric(
        "Avg Attendance Rate",
        f"{avg_attendance:.1%}" if pd.notna(avg_attendance) else "N/A"
    )

    st.markdown("### Activity Mix")

    if "ActivityType" in filtered.columns:
        activity_mix = (
            filtered.groupby("ActivityType")
            .agg(
                Activities=("ActivityType", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                VolunteerHours=("VolunteerHours", "sum")
            )
            .sort_values("TotalVisitors", ascending=False)
        )

        st.dataframe(activity_mix)

        st.bar_chart(activity_mix["TotalVisitors"])

# -----------------------------
# Tab 2: Activity Performance
# -----------------------------

with tab2:
    st.subheader("Which Activities Perform Best?")

    if "ActivityType" in filtered.columns:
        performance = (
            filtered.groupby("ActivityType")
            .agg(
                ActivityCount=("ActivityType", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                MedianVisitors=("TotalVisitors", "median"),
                VolunteerHours=("VolunteerHours", "sum"),
                AvgAttendanceRate=("AttendanceRate", "mean")
            )
            .reset_index()
        )

        performance["VisitorsPerActivityRank"] = performance["AvgVisitors"].rank(ascending=False)
        performance["FrequencyRank"] = performance["ActivityCount"].rank(ascending=False)

        performance = performance.sort_values("AvgVisitors", ascending=False)

        st.dataframe(performance)

        st.markdown("### Best Performing Activity Types by Average Attendance")
        st.bar_chart(performance.set_index("ActivityType")["AvgVisitors"])

        st.markdown("### Recommendation Logic")

        strong_performers = performance[
            (performance["AvgVisitors"] >= performance["AvgVisitors"].median()) &
            (performance["ActivityCount"] <= performance["ActivityCount"].median())
        ]

        saturated = performance[
            (performance["ActivityCount"] >= performance["ActivityCount"].median()) &
            (performance["AvgVisitors"] <= performance["AvgVisitors"].median())
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Potential Growth Opportunities")
            st.caption("Higher attendance but lower frequency.")
            st.dataframe(strong_performers)

        with col2:
            st.markdown("#### Potentially Saturated Categories")
            st.caption("Higher frequency but lower average attendance.")
            st.dataframe(saturated)

# -----------------------------
# Tab 3: Monthly Recommendations
# -----------------------------

with tab3:
    st.subheader("What Activities Do Best by Month?")

    if "Month" in filtered.columns and "ActivityType" in filtered.columns:
        monthly = (
            filtered.groupby(["MonthNum", "Month", "ActivityType"])
            .agg(
                ActivityCount=("ActivityType", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                AvgAttendanceRate=("AttendanceRate", "mean")
            )
            .reset_index()
        )

        monthly = monthly.sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])

        st.markdown("### Monthly Activity Performance")
        st.dataframe(monthly)

        best_by_month = (
            monthly.sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])
            .groupby(["MonthNum", "Month"])
            .head(3)
        )

        st.markdown("### Top Recommended Activity Types by Month")
        st.caption("Based on highest average visitors per activity.")
        st.dataframe(best_by_month)

        selected_month = st.selectbox(
            "Select a month for recommendations",
            sorted(monthly["Month"].dropna().unique(), key=lambda x: month_order.index(x))
        )

        month_recs = best_by_month[best_by_month["Month"] == selected_month]

        st.markdown(f"### Recommended Activities for {selected_month}")

        for _, row in month_recs.iterrows():
            st.write(
                f"**{row['ActivityType']}** tends to perform well in {selected_month}, "
                f"with an average of **{row['AvgVisitors']:.1f} visitors per activity**."
            )

# -----------------------------
# Tab 4: Attendance & No-Shows
# -----------------------------

with tab4:
    st.subheader("Attendance and No-Show Analysis")

    if "VisitorsRegistered" in filtered.columns and "VisitorNoShow" in filtered.columns:
        attendance_summary = (
            filtered.groupby("ActivityType")
            .agg(
                Registered=("VisitorsRegistered", "sum"),
                NoShows=("VisitorNoShow", "sum"),
                ActualVisitors=("ActualVisitors", "sum"),
                AvgAttendanceRate=("AttendanceRate", "mean")
            )
            .reset_index()
        )

        attendance_summary["NoShowRate"] = np.where(
            attendance_summary["Registered"] > 0,
            attendance_summary["NoShows"] / attendance_summary["Registered"],
            np.nan
        )

        attendance_summary = attendance_summary.sort_values("NoShowRate", ascending=False)

        st.dataframe(attendance_summary)

        st.markdown("### No-Show Rate by Activity Type")
        st.bar_chart(attendance_summary.set_index("ActivityType")["NoShowRate"])

        st.markdown("### Stakeholder Talking Points")

        high_no_show = attendance_summary.head(5)

        for _, row in high_no_show.iterrows():
            st.write(
                f"- **{row['ActivityType']}** has a no-show rate of "
                f"**{row['NoShowRate']:.1%}**, which may require reminder emails, waitlists, "
                f"or overbooking strategies."
            )
    else:
        st.info("No-show analysis requires VisitorsRegistered and VisitorNoShow columns.")

# -----------------------------
# Tab 5: Raw Data
# -----------------------------

with tab5:
    st.subheader("Filtered Data")
    st.dataframe(filtered)

    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Filtered Data",
        data=csv,
        file_name="filtered_irc_activity_data.csv",
        mime="text/csv"
    )
