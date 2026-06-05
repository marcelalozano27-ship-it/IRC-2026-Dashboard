import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

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

# -----------------------------
# Cleaning
# -----------------------------

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")
activities["Year"] = activities["Date"].dt.year
activities["Month"] = activities["Date"].dt.month_name()
activities["MonthNum"] = activities["Date"].dt.month
activities["DayOfWeek"] = activities["Date"].dt.day_name()

numeric_cols = [
    "Volunteers", "VolunteerHours", "Staff", "StaffHours",
    "VisitorsRegistered", "VisitorsNoShow", "VisitorsWalkUp",
    "VisitorsChildren", "VisitorsRegisteredIrvineResident",
    "VisitorsRegisteredIrvineNonResident", "TotalVisitors",
    "TotalGuests", "public_visitor_slots"
]

for col in numeric_cols:
    if col in activities.columns:
        activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

public["zip"] = public["zip"].astype(str).str.extract(r"(\d{5})")[0]
public["state_clean"] = public["state"].astype(str).str.strip().str.upper()

state_map = {
    "CA": "California", "CA.": "California", "CALIFORNIA": "California", "CALIF": "California",
    "AZ": "Arizona", "ARIZONA": "Arizona",
    "CO": "Colorado", "COLORADO": "Colorado",
    "DC": "District of Columbia", "DISTRICT OF COLUMBIA": "District of Columbia",
    "FL": "Florida", "FLORIDA": "Florida",
    "GA": "Georgia", "GEORGIA": "Georgia",
    "IA": "Iowa", "IOWA": "Iowa",
    "MA": "Massachusetts", "MASSACHUSETTS": "Massachusetts",
    "MI": "Michigan", "MICHIGAN": "Michigan",
    "MN": "Minnesota", "MINNESOTA": "Minnesota",
    "NH": "New Hampshire", "NEW HAMPSHIRE": "New Hampshire",
    "ND": "North Dakota", "NORTH DAKOTA": "North Dakota",
    "OK": "Oklahoma", "OKLAHOMA": "Oklahoma",
    "TX": "Texas", "TEXAS": "Texas",
    "VA": "Virginia", "VIRGINIA": "Virginia",
    "WV": "West Virginia", "WEST VIRGINIA": "West Virginia"
}

public["state_clean"] = public["state_clean"].map(state_map).fillna(public["state"].astype(str).str.title())

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

# -----------------------------
# Sidebar
# -----------------------------

st.sidebar.header("Filters")

group_col = st.sidebar.selectbox(
    "Analyze activities by",
    ["ActivitySubType", "ActivityType", "ActivityName"],
    index=0
)

filtered = activities.copy()

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

children_filter = st.sidebar.selectbox("Children Included?", ["All", "Yes", "No"])

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

filtered = filtered[filtered["TotalVisitors"].between(visitor_range[0], visitor_range[1])]

public_filtered = public[public["ActivityID"].isin(filtered["ActivityID"])]

states = sorted(public_filtered["state_clean"].dropna().unique())
if len(states) > 0:
    selected_states = st.sidebar.multiselect("Participant State", states, default=states)
    public_filtered = public_filtered[public_filtered["state_clean"].isin(selected_states)]

# -----------------------------
# Scorecard
# -----------------------------

def build_scorecard(df, group_col):
    scorecard = (
        df.groupby(group_col)
        .agg(
            ActivityCount=(group_col, "count"),
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
        .rename(columns={group_col: "ActivityGroup"})
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

scorecard = build_scorecard(filtered, group_col)

tabs = st.tabs([
    "Executive Summary",
    "Activity Scorecard",
    "Opportunity Matrix",
    "Yearly Trends",
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

        st.write(f"- **{top_frequency['ActivityGroup']}** is offered most often with **{int(top_frequency['ActivityCount'])} activities**.")
        st.write(f"- **{top_attendance['ActivityGroup']}** has the highest average attendance with **{top_attendance['AvgVisitors']:.1f} visitors per activity**.")
        st.write(f"- **{top_gap['ActivityGroup']}** appears to be the strongest growth opportunity based on demand relative to supply.")
        st.write(f"- **{top_saturated['ActivityGroup']}** may be oversupplied relative to attendance demand.")

    st.markdown("### Activities by Year")
    yearly = filtered.groupby("Year").size().reset_index(name="ActivityCount")
    fig = px.bar(yearly, x="Year", y="ActivityCount", color="ActivityCount", title="Activities by Year")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Total Visitors by Activity Group")
    visitor_group = scorecard.sort_values("TotalVisitors", ascending=False)
    fig = px.bar(
        visitor_group,
        x="ActivityGroup",
        y="TotalVisitors",
        color="ActivityGroup",
        title=f"Total Visitors by {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

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

    st.markdown("### Average Visitors by Activity Group")
    fig = px.bar(
        scorecard.sort_values("AvgVisitors", ascending=False),
        x="ActivityGroup",
        y="AvgVisitors",
        color="RecommendationCategory",
        title=f"Average Visitors by {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Total Visitors by Activity Group")
    fig = px.bar(
        scorecard.sort_values("TotalVisitors", ascending=False),
        x="ActivityGroup",
        y="TotalVisitors",
        color="ActivityGroup",
        title=f"Total Visitors by {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Recommendation Categories")
    rec_counts = scorecard["RecommendationCategory"].value_counts().reset_index()
    rec_counts.columns = ["RecommendationCategory", "Count"]
    fig = px.pie(rec_counts, names="RecommendationCategory", values="Count", title="Recommendation Category Mix")
    st.plotly_chart(fig, use_container_width=True)

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

    fig = px.scatter(
        matrix,
        x="SupplyScore",
        y="DemandScore",
        size="TotalVisitors",
        color="RecommendationCategory",
        hover_name="ActivityGroup",
        title="Opportunity Matrix: Supply vs Demand"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Growth Opportunities")
    growth = matrix[matrix["RecommendationCategory"] == "Growth Opportunity"]

    if growth.empty:
        st.info("No strong growth opportunities detected with current filters.")
    else:
        for _, row in growth.head(5).iterrows():
            st.success(
                f"Consider expanding **{row['ActivityGroup']}**. "
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
                f"Review **{row['ActivityGroup']}** before adding more offerings. "
                f"It has **{int(row['ActivityCount'])} activities** with "
                f"**{row['AvgVisitors']:.1f} average visitors**."
            )

# -----------------------------
# Yearly Trends
# -----------------------------

with tabs[3]:
    st.subheader("Yearly Trends")

    yearly_type = (
        filtered.groupby(["Year", group_col])
        .agg(
            ActivityCount=(group_col, "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            VolunteerHours=("VolunteerHours", "sum")
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
    )

    st.markdown("### Activity Count by Year and Activity Group")
    fig = px.line(
        yearly_type,
        x="Year",
        y="ActivityCount",
        color="ActivityGroup",
        markers=True,
        title=f"Activity Count by Year and {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Visitors by Year and Activity Group")
    fig = px.line(
        yearly_type,
        x="Year",
        y="TotalVisitors",
        color="ActivityGroup",
        markers=True,
        title=f"Total Visitors by Year and {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Volunteer Hours by Year")
    yearly_vol = filtered.groupby("Year")["VolunteerHours"].sum().reset_index()
    fig = px.bar(
        yearly_vol,
        x="Year",
        y="VolunteerHours",
        color="VolunteerHours",
        title="Volunteer Hours by Year"
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Monthly & Day Recommendations
# -----------------------------

with tabs[4]:
    st.subheader("Monthly & Day Recommendations")

    monthly = (
        filtered.groupby(["MonthNum", "Month", group_col])
        .agg(
            ActivityCount=(group_col, "count"),
            AvgVisitors=("TotalVisitors", "mean"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
        .sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])
    )

    best_by_month = monthly.groupby(["MonthNum", "Month"]).head(3)

    st.markdown("### Top Activity Groups by Month")
    st.dataframe(best_by_month)

    fig = px.bar(
        best_by_month,
        x="Month",
        y="AvgVisitors",
        color="ActivityGroup",
        barmode="group",
        title=f"Top {group_col} by Month"
    )
    st.plotly_chart(fig, use_container_width=True)

    selected_month = st.selectbox(
        "Choose a month",
        [m for m in month_order if m in best_by_month["Month"].unique()]
    )

    month_recs = best_by_month[best_by_month["Month"] == selected_month]

    st.markdown(f"### Recommendations for {selected_month}")
    for _, row in month_recs.iterrows():
        st.info(
            f"**{row['ActivityGroup']}** performs well in **{selected_month}**, "
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
        .reset_index()
    )

    st.markdown("### Best Days of Week")
    st.dataframe(day_summary)

    fig = px.bar(
        day_summary,
        x="DayOfWeek",
        y="AvgVisitors",
        color="DayOfWeek",
        title="Average Visitors by Day of Week"
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Attendance & No-Shows
# -----------------------------

with tabs[5]:
    st.subheader("Attendance and No-Show Analysis")

    attendance = (
        filtered.groupby(group_col)
        .agg(
            Registered=("VisitorsRegistered", "sum"),
            NoShows=("VisitorsNoShow", "sum"),
            WalkUps=("VisitorsWalkUp", "sum"),
            ActualVisitors=("ActualVisitors", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
        .sort_values("AvgNoShowRate", ascending=False)
    )

    st.dataframe(attendance)

    fig = px.bar(
        attendance,
        x="ActivityGroup",
        y="AvgNoShowRate",
        color="ActivityGroup",
        title=f"No-Show Rate by {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### No-Show Recommendations")

    for _, row in attendance.head(5).iterrows():
        st.warning(
            f"**{row['ActivityGroup']}** has an average no-show rate of **{row['AvgNoShowRate']:.1%}**. "
            f"Consider reminders, waitlists, or adjusted overbooking assumptions."
        )

# -----------------------------
# Geography
# -----------------------------

with tabs[6]:
    st.subheader("Participant Geography")

    st.caption("Uses city, state, and ZIP fields from public signup records.")

    state_summary = (
        public_filtered.groupby("state_clean")
        .agg(
            TotalSignups=("public_spaces_reserved", "sum"),
            UniqueBookings=("booking_id", "nunique")
        )
        .reset_index()
        .sort_values("TotalSignups", ascending=False)
    )

    st.markdown("### Participant Signups by State")
    fig = px.bar(
        state_summary,
        x="state_clean",
        y="TotalSignups",
        color="state_clean",
        title="Participant Signups by State"
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Top Participant Cities")
        city_summary = (
            public_filtered.groupby(["city", "state_clean"])
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

# -----------------------------
# Volunteer Analysis
# -----------------------------

with tabs[7]:
    st.subheader("Volunteer Analysis")

    volunteer_summary = (
        filtered.groupby(group_col)
        .agg(
            ActivityCount=(group_col, "count"),
            Volunteers=("Volunteers", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean")
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
    )

    volunteer_summary["VisitorsPerVolunteerHour"] = np.where(
        volunteer_summary["VolunteerHours"] > 0,
        volunteer_summary["TotalVisitors"] / volunteer_summary["VolunteerHours"],
        np.nan
    )

    st.dataframe(volunteer_summary.sort_values("VolunteerHours", ascending=False))

    fig = px.bar(
        volunteer_summary.sort_values("VolunteerHours", ascending=False),
        x="ActivityGroup",
        y="VolunteerHours",
        color="ActivityGroup",
        title=f"Volunteer Hours by {group_col}"
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Raw Data
# -----------------------------

with tabs[8]:
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
