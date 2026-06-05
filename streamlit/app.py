import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="IRC Activity Planning Dashboard", layout="wide")

st.title("IRC Activity Planning Dashboard")
st.caption("Decision-support dashboard for attendance trends, activity gaps, and stakeholder recommendations.")

@st.cache_data
def load_data():
    activities = pd.read_csv("data/activity_level.csv")
    public = pd.read_csv("data/public_signups.csv")
    volunteers = pd.read_csv("data/volunteer_signups.csv")
    return activities, public, volunteers

activities, public, volunteers = load_data()

# Clean column names
activities.columns = (
    activities.columns
    .str.strip()
    .str.replace(" ", "", regex=False)
    .str.replace("_", "", regex=False)
)

public.columns = (
    public.columns
    .str.strip()
    .str.replace(" ", "", regex=False)
    .str.replace("_", "", regex=False)
)

volunteers.columns = (
    volunteers.columns
    .str.strip()
    .str.replace(" ", "", regex=False)
    .str.replace("_", "", regex=False)
)

# Date cleanup
date_candidates = ["Date", "eventstartdate", "EventStartDate", "ActivityDate"]
date_col = next((c for c in date_candidates if c in activities.columns), None)

if date_col:
    activities[date_col] = pd.to_datetime(activities[date_col], errors="coerce")
    activities["Year"] = activities[date_col].dt.year
    activities["Month"] = activities[date_col].dt.month_name()
    activities["MonthNum"] = activities[date_col].dt.month
    activities["DayOfWeek"] = activities[date_col].dt.day_name()

# Numeric cleanup
for col in ["TotalVisitors", "VolunteerHours", "VisitorsRegistered", "VisitorNoShow", "WalkUp", "Volunteers"]:
    if col in activities.columns:
        activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

if "VisitorsRegistered" in activities.columns and "VisitorNoShow" in activities.columns:
    activities["ActualVisitors"] = activities["VisitorsRegistered"] - activities["VisitorNoShow"]
    activities["AttendanceRate"] = np.where(
        activities["VisitorsRegistered"] > 0,
        activities["ActualVisitors"] / activities["VisitorsRegistered"],
        np.nan
    )
    activities["NoShowRate"] = np.where(
        activities["VisitorsRegistered"] > 0,
        activities["VisitorNoShow"] / activities["VisitorsRegistered"],
        np.nan
    )
else:
    activities["ActualVisitors"] = activities["TotalVisitors"] if "TotalVisitors" in activities.columns else 0
    activities["AttendanceRate"] = np.nan
    activities["NoShowRate"] = np.nan

# Sidebar filters
st.sidebar.header("Filters")

filtered = activities.copy()

if "ActivityType" in activities.columns:
    activity_types = sorted(activities["ActivityType"].dropna().unique())
    selected_types = st.sidebar.multiselect("Activity Type", activity_types, default=activity_types)
    filtered = filtered[filtered["ActivityType"].isin(selected_types)]

if "Year" in activities.columns and activities["Year"].notna().any():
    years = sorted(activities["Year"].dropna().astype(int).unique())
    selected_years = st.sidebar.multiselect("Year", years, default=years)
    filtered = filtered[filtered["Year"].isin(selected_years)]

if "Month" in activities.columns:
    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    available_months = [m for m in month_order if m in activities["Month"].dropna().unique()]
    selected_months = st.sidebar.multiselect("Month", available_months, default=available_months)
    filtered = filtered[filtered["Month"].isin(selected_months)]

if "TotalVisitors" in activities.columns:
    visitor_range = st.sidebar.slider(
        "Total Visitors Range",
        int(activities["TotalVisitors"].min()),
        int(activities["TotalVisitors"].max()),
        (int(activities["TotalVisitors"].min()), int(activities["TotalVisitors"].max()))
    )
    filtered = filtered[filtered["TotalVisitors"].between(visitor_range[0], visitor_range[1])]

tabs = st.tabs([
    "Executive Summary",
    "Activity Scorecard",
    "Opportunity Matrix",
    "Monthly & Day Recommendations",
    "Attendance & No-Shows",
    "Volunteer Analysis",
    "Geography",
    "Raw Data"
])

# Executive Summary
with tabs[0]:
    st.subheader("Executive Summary")

    total_activities = len(filtered)
    total_visitors = filtered["TotalVisitors"].sum() if "TotalVisitors" in filtered.columns else 0
    avg_visitors = filtered["TotalVisitors"].mean() if "TotalVisitors" in filtered.columns else 0
    volunteer_hours = filtered["VolunteerHours"].sum() if "VolunteerHours" in filtered.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Activities", f"{total_activities:,}")
    col2.metric("Total Visitors", f"{int(total_visitors):,}")
    col3.metric("Avg Visitors / Activity", f"{avg_visitors:.1f}")
    col4.metric("Volunteer Hours", f"{volunteer_hours:,.1f}")

    if "ActivityType" in filtered.columns and "TotalVisitors" in filtered.columns:
        summary = (
            filtered.groupby("ActivityType")
            .agg(
                ActivityCount=("ActivityType", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean")
            )
            .reset_index()
        )

        top_volume = summary.sort_values("ActivityCount", ascending=False).iloc[0]
        top_attendance = summary.sort_values("AvgVisitors", ascending=False).iloc[0]

        st.markdown("### Key Findings")
        st.write(f"- **{top_volume['ActivityType']}** is the most frequently offered activity type.")
        st.write(f"- **{top_attendance['ActivityType']}** has the highest average attendance per activity.")
        st.write("- Use the Opportunity Matrix tab to identify growth opportunities and possible oversaturation.")
        st.write("- Use the Monthly & Day Recommendations tab to guide when activities should be scheduled.")

# Activity Scorecard
with tabs[1]:
    st.subheader("Activity Scorecard")

    scorecard = (
        filtered.groupby("ActivityType")
        .agg(
            ActivityCount=("ActivityType", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            MedianVisitors=("TotalVisitors", "median"),
            VolunteerHours=("VolunteerHours", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reset_index()
    )

    scorecard["DemandLevel"] = pd.qcut(scorecard["AvgVisitors"].rank(method="first"), 3, labels=["Low", "Medium", "High"])
    scorecard["SupplyLevel"] = pd.qcut(scorecard["ActivityCount"].rank(method="first"), 3, labels=["Low", "Medium", "High"])

    scorecard["Recommendation"] = np.select(
        [
            (scorecard["DemandLevel"] == "High") & (scorecard["SupplyLevel"] == "Low"),
            (scorecard["DemandLevel"] == "High") & (scorecard["SupplyLevel"] == "High"),
            (scorecard["DemandLevel"] == "Low") & (scorecard["SupplyLevel"] == "High"),
        ],
        [
            "Expand or test more",
            "Core program",
            "Review for oversaturation"
        ],
        default="Monitor"
    )

    st.dataframe(scorecard.sort_values("AvgVisitors", ascending=False))
    st.bar_chart(scorecard.set_index("ActivityType")["AvgVisitors"])

# Opportunity Matrix
with tabs[2]:
    st.subheader("Opportunity Matrix")

    matrix = scorecard.copy()
    matrix["SupplyScore"] = matrix["ActivityCount"] / matrix["ActivityCount"].max()
    matrix["DemandScore"] = matrix["AvgVisitors"] / matrix["AvgVisitors"].max()
    matrix["GapScore"] = matrix["DemandScore"] - matrix["SupplyScore"]

    matrix["Quadrant"] = np.select(
        [
            (matrix["DemandScore"] >= matrix["DemandScore"].median()) & (matrix["SupplyScore"] < matrix["SupplyScore"].median()),
            (matrix["DemandScore"] >= matrix["DemandScore"].median()) & (matrix["SupplyScore"] >= matrix["SupplyScore"].median()),
            (matrix["DemandScore"] < matrix["DemandScore"].median()) & (matrix["SupplyScore"] >= matrix["SupplyScore"].median()),
        ],
        [
            "Growth Opportunity",
            "Core Program",
            "Possible Oversaturation"
        ],
        default="Low Priority / Monitor"
    )

    st.dataframe(matrix.sort_values("GapScore", ascending=False))

    st.markdown("### Recommendations")
    for _, row in matrix.sort_values("GapScore", ascending=False).head(5).iterrows():
        st.success(
            f"**{row['ActivityType']}**: {row['Quadrant']}. "
            f"Avg visitors/activity: {row['AvgVisitors']:.1f}. "
            f"Activity count: {int(row['ActivityCount'])}."
        )

    for _, row in matrix.sort_values("GapScore").head(3).iterrows():
        st.warning(
            f"Review **{row['ActivityType']}** before adding more. "
            f"It may have higher supply relative to demand."
        )

# Monthly and Day Recommendations
with tabs[3]:
    st.subheader("Best Activities by Month and Day")

    if "Month" in filtered.columns:
        monthly = (
            filtered.groupby(["MonthNum", "Month", "ActivityType"])
            .agg(
                ActivityCount=("ActivityType", "count"),
                AvgVisitors=("TotalVisitors", "mean"),
                TotalVisitors=("TotalVisitors", "sum")
            )
            .reset_index()
            .sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])
        )

        best_by_month = monthly.groupby(["MonthNum", "Month"]).head(3)

        st.markdown("### Top Activity Types by Month")
        st.dataframe(best_by_month)

        selected_month = st.selectbox("Choose a month", best_by_month["Month"].dropna().unique())

        month_recs = best_by_month[best_by_month["Month"] == selected_month]

        for _, row in month_recs.iterrows():
            st.info(
                f"In **{selected_month}**, **{row['ActivityType']}** performs well, "
                f"averaging **{row['AvgVisitors']:.1f} visitors per activity**."
            )

    if "DayOfWeek" in filtered.columns:
        day_summary = (
            filtered.groupby("DayOfWeek")
            .agg(
                ActivityCount=("DayOfWeek", "count"),
                AvgVisitors=("TotalVisitors", "mean"),
                TotalVisitors=("TotalVisitors", "sum")
            )
            .sort_values("AvgVisitors", ascending=False)
        )

        st.markdown("### Best Days of Week")
        st.dataframe(day_summary)
        st.bar_chart(day_summary["AvgVisitors"])

# Attendance and No Shows
with tabs[4]:
    st.subheader("Attendance and No-Show Analysis")

    if "VisitorsRegistered" in filtered.columns and "VisitorNoShow" in filtered.columns:
        attendance = (
            filtered.groupby("ActivityType")
            .agg(
                Registered=("VisitorsRegistered", "sum"),
                NoShows=("VisitorNoShow", "sum"),
                ActualVisitors=("ActualVisitors", "sum"),
                AvgAttendanceRate=("AttendanceRate", "mean"),
                AvgNoShowRate=("NoShowRate", "mean")
            )
            .reset_index()
            .sort_values("AvgNoShowRate", ascending=False)
        )

        st.dataframe(attendance)
        st.bar_chart(attendance.set_index("ActivityType")["AvgNoShowRate"])

        st.markdown("### No-Show Recommendations")
        for _, row in attendance.head(5).iterrows():
            st.warning(
                f"**{row['ActivityType']}** has an average no-show rate of "
                f"**{row['AvgNoShowRate']:.1%}**. Consider reminder emails, waitlists, or overbooking."
            )
    else:
        st.info("No-show analysis requires VisitorsRegistered and VisitorNoShow columns.")

# Volunteer Analysis
with tabs[5]:
    st.subheader("Volunteer Effectiveness")

    if "VolunteerHours" in filtered.columns:
        volunteer_summary = (
            filtered.groupby("ActivityType")
            .agg(
                ActivityCount=("ActivityType", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                VolunteerHours=("VolunteerHours", "sum"),
                AvgVolunteerHours=("VolunteerHours", "mean")
            )
            .reset_index()
        )

        volunteer_summary["VisitorsPerVolunteerHour"] = np.where(
            volunteer_summary["VolunteerHours"] > 0,
            volunteer_summary["TotalVisitors"] / volunteer_summary["VolunteerHours"],
            np.nan
        )

        st.dataframe(volunteer_summary.sort_values("VolunteerHours", ascending=False))

        st.markdown("### Volunteer Hours by Activity Type")
        st.bar_chart(volunteer_summary.set_index("ActivityType")["VolunteerHours"])

# Geography
with tabs[6]:
    st.subheader("Geographic Participant Analysis")

    st.caption("This uses public signup data if city, state, or zip fields are available.")

    geo_cols = public.columns.tolist()
    st.write("Available public signup columns:", geo_cols)

    possible_city = next((c for c in public.columns if c.lower() in ["city", "usercity"]), None)
    possible_state = next((c for c in public.columns if c.lower() in ["state", "userstate"]), None)
    possible_zip = next((c for c in public.columns if c.lower() in ["zip", "zipcode", "postalcode"]), None)

    if possible_city:
        city_summary = public[possible_city].value_counts().head(20)
        st.markdown("### Top Participant Cities")
        st.dataframe(city_summary)
        st.bar_chart(city_summary)

    if possible_state:
        state_summary = public[possible_state].value_counts().head(20)
        st.markdown("### Top Participant States")
        st.dataframe(state_summary)

    if possible_zip:
        zip_summary = public[possible_zip].value_counts().head(20)
        st.markdown("### Top Participant Zip Codes")
        st.dataframe(zip_summary)

    if not any([possible_city, possible_state, possible_zip]):
        st.info("No city, state, or zip columns detected yet.")

# Raw Data
with tabs[7]:
    st.subheader("Filtered Activity Data")
    st.dataframe(filtered)

    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Filtered Data",
        data=csv,
        file_name="filtered_activity_data.csv",
        mime="text/csv"
    )
