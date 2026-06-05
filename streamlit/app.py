import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="IRC Activity Planning Dashboard", layout="wide")

st.title("IRC Activity Planning Dashboard")
st.caption("Decision-support dashboard for attendance trends, activity gaps, recommendations, and participant geography.")

@st.cache_data
def load_data():
    activities = pd.read_csv("data/activity_level.csv")
    public = pd.read_csv("data/public_signups.csv")
    volunteers = pd.read_csv("data/volunteer_signups.csv")
    return activities, public, volunteers

activities, public, volunteers = load_data()

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")
activities["event_start_date"] = pd.to_datetime(activities["event_start_date"], errors="coerce")

activities["Year"] = activities["Date"].dt.year
activities["Month"] = activities["Date"].dt.month_name()
activities["MonthNum"] = activities["Date"].dt.month
activities["DayOfWeek"] = activities["Date"].dt.day_name()

numeric_cols = [
    "Volunteers", "VolunteerHours", "Staff", "StaffHours",
    "VisitorsRegistered", "VisitorsNoShow", "VisitorsWalkUp",
    "VisitorsChildren", "TotalVisitors", "TotalGuests",
    "public_visitor_slots"
]

for col in numeric_cols:
    if col in activities.columns:
        activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

activities["ActualVisitors"] = activities["VisitorsRegistered"] - activities["VisitorsNoShow"]

activities["AttendanceRate"] = np.where(
    activities["VisitorsRegistered"] > 0,
    activities["ActualVisitors"] / activities["VisitorsRegistered"],
    np.nan
)

activities["NoShowRate"] = np.where(
    activities["VisitorsRegistered"] > 0,
    activities["VisitorsNoShow"] / activities["VisitorsRegistered"],
    np.nan
)

activities["FillRate"] = np.where(
    activities["public_visitor_slots"] > 0,
    activities["VisitorsRegistered"] / activities["public_visitor_slots"],
    np.nan
)

public["zip"] = public["zip"].astype(str).str.extract(r"(\d{5})")[0]

# -----------------------------
# Sidebar Filters
# -----------------------------

st.sidebar.header("Filters")

filtered = activities.copy()
public_filtered = public.copy()

activity_types = sorted(activities["ActivityType"].dropna().unique())
selected_types = st.sidebar.multiselect("Activity Type", activity_types, default=activity_types)
filtered = filtered[filtered["ActivityType"].isin(selected_types)]

subtypes = sorted(filtered["ActivitySubType"].dropna().unique())
selected_subtypes = st.sidebar.multiselect("Activity Subtype", subtypes, default=subtypes)
filtered = filtered[filtered["ActivitySubType"].isin(selected_subtypes)]

years = sorted(filtered["Year"].dropna().astype(int).unique())
selected_years = st.sidebar.multiselect("Year", years, default=years)
filtered = filtered[filtered["Year"].isin(selected_years)]

month_order = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

available_months = [m for m in month_order if m in filtered["Month"].dropna().unique()]
selected_months = st.sidebar.multiselect("Month", available_months, default=available_months)
filtered = filtered[filtered["Month"].isin(selected_months)]

days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
available_days = [d for d in days_order if d in filtered["DayOfWeek"].dropna().unique()]
selected_days = st.sidebar.multiselect("Day of Week", available_days, default=available_days)
filtered = filtered[filtered["DayOfWeek"].isin(selected_days)]

statuses = sorted(filtered["ActivityStatus"].dropna().unique())
selected_statuses = st.sidebar.multiselect("Activity Status", statuses, default=statuses)
filtered = filtered[filtered["ActivityStatus"].isin(selected_statuses)]

children_filter = st.sidebar.selectbox(
    "Children Included?",
    ["All", "Yes", "No"]
)

if children_filter == "Yes":
    filtered = filtered[filtered["VisitorsChildren"] > 0]
elif children_filter == "No":
    filtered = filtered[filtered["VisitorsChildren"] == 0]

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

# Match public signup data to filtered activities
public_filtered = public[public["ActivityID"].isin(filtered["ActivityID"])]

states = sorted(public_filtered["state"].dropna().unique())
if len(states) > 0:
    selected_states = st.sidebar.multiselect("Participant State", states, default=states)
    public_filtered = public_filtered[public_filtered["state"].isin(selected_states)]

cities = sorted(public_filtered["city"].dropna().unique())
if len(cities) > 0:
    selected_cities = st.sidebar.multiselect("Participant City", cities, default=cities)
    public_filtered = public_filtered[public_filtered["city"].isin(selected_cities)]

# -----------------------------
# Scorecard Function
# -----------------------------

def build_scorecard(df):
    scorecard = (
        df.groupby("ActivityType")
        .agg(
            ActivityCount=("ActivityType", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            MedianVisitors=("TotalVisitors", "median"),
            Registered=("VisitorsRegistered", "sum"),
            NoShows=("VisitorsNoShow", "sum"),
            WalkUps=("VisitorsWalkUp", "sum"),
            Children=("VisitorsChildren", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean"),
            AvgFillRate=("FillRate", "mean")
        )
        .reset_index()
    )

    if scorecard.empty:
        return scorecard

    scorecard["SupplyScore"] = scorecard["ActivityCount"] / scorecard["ActivityCount"].max()
    scorecard["DemandScore"] = scorecard["AvgVisitors"] / scorecard["AvgVisitors"].max()
    scorecard["GapScore"] = scorecard["DemandScore"] - scorecard["SupplyScore"]

    scorecard["RecommendationCategory"] = np.select(
        [
            scorecard["GapScore"] >= 0.20,
            scorecard["GapScore"] <= -0.20,
            (
                scorecard["DemandScore"] >= scorecard["DemandScore"].median()
            )
            & (
                scorecard["SupplyScore"] >= scorecard["SupplyScore"].median()
            )
        ],
        [
            "Growth Opportunity",
            "Possible Oversaturation",
            "Core Program"
        ],
        default="Monitor"
    )

    return scorecard


scorecard = build_scorecard(filtered)

tabs = st.tabs([
    "Executive Summary",
    "Activity Scorecard",
    "Opportunity Matrix",
    "Monthly & Day Recommendations",
    "Attendance & No-Shows",
    "Geography",
    "Volunteer Analysis",
    "Raw Data"
])

# -----------------------------
# Executive Summary
# -----------------------------

with tabs[0]:
    st.subheader("Executive Summary")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Activities", f"{len(filtered):,}")
    col2.metric("Total Visitors", f"{int(filtered['TotalVisitors'].sum()):,}")
    col3.metric("Avg Visitors / Activity", f"{filtered['TotalVisitors'].mean():.1f}")
    col4.metric("No-Show Rate", f"{filtered['NoShowRate'].mean():.1%}")
    col5.metric("Volunteer Hours", f"{filtered['VolunteerHours'].sum():,.1f}")

    st.markdown("### Key Findings")

    if not scorecard.empty:
        top_frequency = scorecard.sort_values("ActivityCount", ascending=False).iloc[0]
        top_attendance = scorecard.sort_values("AvgVisitors", ascending=False).iloc[0]
        top_gap = scorecard.sort_values("GapScore", ascending=False).iloc[0]
        top_saturated = scorecard.sort_values("GapScore").iloc[0]

        st.write(f"- **{top_frequency['ActivityType']}** is offered most often with **{int(top_frequency['ActivityCount'])} activities**.")
        st.write(f"- **{top_attendance['ActivityType']}** has the highest average attendance with **{top_attendance['AvgVisitors']:.1f} visitors per activity**.")
        st.write(f"- **{top_gap['ActivityType']}** appears to be the strongest growth opportunity based on demand relative to supply.")
        st.write(f"- **{top_saturated['ActivityType']}** may be oversupplied relative to attendance demand.")

    st.info(
        "Use this dashboard to identify which activities should be expanded, which may be oversaturated, "
        "which months and days perform best, and where participants are coming from."
    )

# -----------------------------
# Activity Scorecard
# -----------------------------

with tabs[1]:
    st.subheader("Activity Scorecard")

    st.dataframe(scorecard.sort_values("AvgVisitors", ascending=False))

    st.markdown("### Average Visitors by Activity Type")
    st.bar_chart(scorecard.set_index("ActivityType")["AvgVisitors"])

    st.markdown("### Recommendation Categories")
    st.bar_chart(scorecard["RecommendationCategory"].value_counts())

# -----------------------------
# Opportunity Matrix
# -----------------------------

with tabs[2]:
    st.subheader("Opportunity Matrix")

    st.markdown("""
    This compares **supply** and **demand**.

    - **Supply** = number of activities offered
    - **Demand** = average visitors per activity
    - **Growth Opportunity** = high demand but lower supply
    - **Possible Oversaturation** = high supply but lower demand
    """)

    matrix = scorecard.sort_values("GapScore", ascending=False)
    st.dataframe(matrix)

    st.markdown("### Growth Opportunities")
    growth = matrix[matrix["RecommendationCategory"] == "Growth Opportunity"]

    if growth.empty:
        st.info("No strong growth opportunities detected with current filters.")
    else:
        for _, row in growth.head(5).iterrows():
            st.success(
                f"Consider expanding **{row['ActivityType']}**. "
                f"It averages **{row['AvgVisitors']:.1f} visitors per activity** "
                f"across **{int(row['ActivityCount'])} activities**."
            )

    st.markdown("### Possible Oversaturation")
    saturated = matrix[matrix["RecommendationCategory"] == "Possible Oversaturation"]

    if saturated.empty:
        st.info("No major oversaturation detected with current filters.")
    else:
        for _, row in saturated.head(5).iterrows():
            st.warning(
                f"Review **{row['ActivityType']}** before adding more offerings. "
                f"It has **{int(row['ActivityCount'])} activities** with "
                f"**{row['AvgVisitors']:.1f} average visitors**."
            )

# -----------------------------
# Monthly & Day Recommendations
# -----------------------------

with tabs[3]:
    st.subheader("Monthly & Day Recommendations")

    monthly = (
        filtered.groupby(["MonthNum", "Month", "ActivityType"])
        .agg(
            ActivityCount=("ActivityType", "count"),
            AvgVisitors=("TotalVisitors", "mean"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reset_index()
        .sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])
    )

    best_by_month = monthly.groupby(["MonthNum", "Month"]).head(3)

    st.markdown("### Top Activity Types by Month")
    st.dataframe(best_by_month)

    selected_month = st.selectbox(
        "Choose a month",
        [m for m in month_order if m in best_by_month["Month"].unique()]
    )

    month_recs = best_by_month[best_by_month["Month"] == selected_month]

    st.markdown(f"### Recommendations for {selected_month}")
    for _, row in month_recs.iterrows():
        st.info(
            f"**{row['ActivityType']}** performs well in **{selected_month}**, "
            f"averaging **{row['AvgVisitors']:.1f} visitors per activity**."
        )

    day_summary = (
        filtered.groupby("DayOfWeek")
        .agg(
            ActivityCount=("DayOfWeek", "count"),
            AvgVisitors=("TotalVisitors", "mean"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reindex(days_order)
        .dropna(how="all")
    )

    st.markdown("### Best Days of Week")
    st.dataframe(day_summary)
    st.bar_chart(day_summary["AvgVisitors"])

# -----------------------------
# Attendance & No-Shows
# -----------------------------

with tabs[4]:
    st.subheader("Attendance and No-Show Analysis")

    attendance = (
        filtered.groupby("ActivityType")
        .agg(
            Registered=("VisitorsRegistered", "sum"),
            NoShows=("VisitorsNoShow", "sum"),
            WalkUps=("VisitorsWalkUp", "sum"),
            ActualVisitors=("ActualVisitors", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reset_index()
        .sort_values("AvgNoShowRate", ascending=False)
    )

    st.dataframe(attendance)

    st.markdown("### No-Show Rate by Activity Type")
    st.bar_chart(attendance.set_index("ActivityType")["AvgNoShowRate"])

    st.markdown("### No-Show Recommendations")

    for _, row in attendance.head(5).iterrows():
        st.warning(
            f"**{row['ActivityType']}** has an average no-show rate of **{row['AvgNoShowRate']:.1%}**. "
            f"Consider reminders, waitlists, or adjusted overbooking assumptions."
        )

# -----------------------------
# Geography
# -----------------------------

with tabs[5]:
    st.subheader("Participant Geography")

    st.caption("Uses city, state, and ZIP fields from public signup records.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Top Participant Cities")

        city_summary = (
            public_filtered.groupby(["city", "state"])
            .agg(
                TotalSignups=("public_spaces_reserved", "sum"),
                UniqueBookings=("booking_id", "nunique")
            )
            .reset_index()
            .sort_values("TotalSignups", ascending=False)
        )

        st.dataframe(city_summary.head(25))

    with col2:
        st.markdown("### Top ZIP Codes")

        zip_summary = (
            public_filtered.groupby("zip")
            .agg(
                TotalSignups=("public_spaces_reserved", "sum"),
                UniqueBookings=("booking_id", "nunique")
            )
            .reset_index()
            .sort_values("TotalSignups", ascending=False)
        )

        st.dataframe(zip_summary.head(25))

    st.markdown("### City Signup Volume")
    if not city_summary.empty:
        city_chart = city_summary.head(15).copy()
        city_chart["CityState"] = city_chart["city"] + ", " + city_chart["state"]
        st.bar_chart(city_chart.set_index("CityState")["TotalSignups"])

# -----------------------------
# Volunteer Analysis
# -----------------------------

with tabs[6]:
    st.subheader("Volunteer Analysis")

    volunteer_summary = (
        filtered.groupby("ActivityType")
        .agg(
            ActivityCount=("ActivityType", "count"),
            Volunteers=("Volunteers", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean")
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

# -----------------------------
# Raw Data
# -----------------------------

with tabs[7]:
    st.subheader("Filtered Activity Data")
    st.dataframe(filtered)

    st.subheader("Filtered Public Signup Data")
    st.dataframe(public_filtered)

    st.subheader("Volunteer Signup Data")
    st.dataframe(volunteers)

    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Filtered Activity Data",
        data=csv,
        file_name="filtered_activity_data.csv",
        mime="text/csv"
    )
