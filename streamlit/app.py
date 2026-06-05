import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="IRC Activity Planning Dashboard", layout="wide")

st.title("IRC Activity Planning Dashboard")
st.caption(
    "Decision-support dashboard for attendance trends, activity gaps, "
    "stakeholder recommendations, and participant geography."
)

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
# Helper Functions
# -----------------------------

def clean_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "", regex=False)
        .str.replace("_", "", regex=False)
        .str.replace("-", "", regex=False)
    )
    return df


def find_col(df, keywords):
    for col in df.columns:
        col_lower = col.lower()
        if all(keyword.lower() in col_lower for keyword in keywords):
            return col
    return None


def find_any_col(df, keywords):
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword.lower() in col_lower for keyword in keywords):
            return col
    return None


activities = clean_columns(activities)
public = clean_columns(public)
volunteers = clean_columns(volunteers)

# -----------------------------
# Column Detection
# -----------------------------

activity_type_col = find_any_col(activities, ["activitytype", "type"])
title_col = find_any_col(activities, ["title", "activityname", "name"])
total_visitors_col = find_any_col(activities, ["totalvisitors", "visitors"])
volunteer_hours_col = find_any_col(activities, ["volunteerhours", "hours"])

registered_col = find_any_col(
    activities,
    ["visitorsregistered", "registered", "reserved", "publicspacesreserved"]
)

noshow_col = find_any_col(
    activities,
    ["visitornoshow", "noshow", "noshows", "absent"]
)

date_col = find_any_col(
    activities,
    ["date", "eventstartdate", "activitydate", "startdate"]
)

zip_col_public = find_any_col(public, ["zip", "zipcode", "postal"])
city_col_public = find_any_col(public, ["city"])
state_col_public = find_any_col(public, ["state"])

# -----------------------------
# Basic Cleaning
# -----------------------------

if date_col:
    activities[date_col] = pd.to_datetime(activities[date_col], errors="coerce")
    activities["Year"] = activities[date_col].dt.year
    activities["Month"] = activities[date_col].dt.month_name()
    activities["MonthNum"] = activities[date_col].dt.month
    activities["DayOfWeek"] = activities[date_col].dt.day_name()

if total_visitors_col:
    activities[total_visitors_col] = pd.to_numeric(
        activities[total_visitors_col], errors="coerce"
    ).fillna(0)
    activities["TotalVisitorsClean"] = activities[total_visitors_col]
else:
    activities["TotalVisitorsClean"] = 0

if volunteer_hours_col:
    activities[volunteer_hours_col] = pd.to_numeric(
        activities[volunteer_hours_col], errors="coerce"
    ).fillna(0)
    activities["VolunteerHoursClean"] = activities[volunteer_hours_col]
else:
    activities["VolunteerHoursClean"] = 0

if registered_col:
    activities[registered_col] = pd.to_numeric(
        activities[registered_col], errors="coerce"
    ).fillna(0)

if noshow_col:
    activities[noshow_col] = pd.to_numeric(
        activities[noshow_col], errors="coerce"
    ).fillna(0)

if registered_col and noshow_col:
    activities["ActualVisitors"] = activities[registered_col] - activities[noshow_col]
    activities["AttendanceRate"] = np.where(
        activities[registered_col] > 0,
        activities["ActualVisitors"] / activities[registered_col],
        np.nan
    )
    activities["NoShowRate"] = np.where(
        activities[registered_col] > 0,
        activities[noshow_col] / activities[registered_col],
        np.nan
    )
else:
    activities["ActualVisitors"] = activities["TotalVisitorsClean"]
    activities["AttendanceRate"] = np.nan
    activities["NoShowRate"] = np.nan


# -----------------------------
# Sidebar Filters
# -----------------------------

st.sidebar.header("Filters")

filtered = activities.copy()

if activity_type_col:
    activity_types = sorted(filtered[activity_type_col].dropna().unique())
    selected_types = st.sidebar.multiselect(
        "Activity Type",
        activity_types,
        default=activity_types
    )
    filtered = filtered[filtered[activity_type_col].isin(selected_types)]

if "Year" in filtered.columns and filtered["Year"].notna().any():
    years = sorted(filtered["Year"].dropna().astype(int).unique())
    selected_years = st.sidebar.multiselect(
        "Year",
        years,
        default=years
    )
    filtered = filtered[filtered["Year"].isin(selected_years)]

if "Month" in filtered.columns:
    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    available_months = [
        m for m in month_order if m in filtered["Month"].dropna().unique()
    ]
    selected_months = st.sidebar.multiselect(
        "Month",
        available_months,
        default=available_months
    )
    filtered = filtered[filtered["Month"].isin(selected_months)]

if filtered["TotalVisitorsClean"].notna().any():
    min_visitors = int(filtered["TotalVisitorsClean"].min())
    max_visitors = int(filtered["TotalVisitorsClean"].max())

    if min_visitors < max_visitors:
        visitor_range = st.sidebar.slider(
            "Total Visitors Range",
            min_value=min_visitors,
            max_value=max_visitors,
            value=(min_visitors, max_visitors)
        )
        filtered = filtered[
            filtered["TotalVisitorsClean"].between(visitor_range[0], visitor_range[1])
        ]

with st.sidebar.expander("Detected Columns"):
    st.write("Activity Type:", activity_type_col)
    st.write("Total Visitors:", total_visitors_col)
    st.write("Volunteer Hours:", volunteer_hours_col)
    st.write("Registered:", registered_col)
    st.write("No Show:", noshow_col)
    st.write("Date:", date_col)
    st.write("Public ZIP:", zip_col_public)
    st.write("Public City:", city_col_public)
    st.write("Public State:", state_col_public)


# -----------------------------
# Shared Aggregations
# -----------------------------

def build_scorecard(df):
    if not activity_type_col:
        return pd.DataFrame()

    scorecard = (
        df.groupby(activity_type_col)
        .agg(
            ActivityCount=(activity_type_col, "count"),
            TotalVisitors=("TotalVisitorsClean", "sum"),
            AvgVisitors=("TotalVisitorsClean", "mean"),
            MedianVisitors=("TotalVisitorsClean", "median"),
            VolunteerHours=("VolunteerHoursClean", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean")
        )
        .reset_index()
        .rename(columns={activity_type_col: "ActivityType"})
    )

    if len(scorecard) > 0:
        scorecard["SupplyScore"] = scorecard["ActivityCount"] / scorecard["ActivityCount"].max()
        scorecard["DemandScore"] = scorecard["AvgVisitors"] / scorecard["AvgVisitors"].max()
        scorecard["GapScore"] = scorecard["DemandScore"] - scorecard["SupplyScore"]

        scorecard["RecommendationCategory"] = np.select(
            [
                scorecard["GapScore"] >= 0.20,
                scorecard["GapScore"] <= -0.20,
                (scorecard["DemandScore"] >= scorecard["DemandScore"].median())
                & (scorecard["SupplyScore"] >= scorecard["SupplyScore"].median())
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


# -----------------------------
# Tabs
# -----------------------------

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


# -----------------------------
# Executive Summary
# -----------------------------

with tabs[0]:
    st.subheader("Executive Summary")

    total_activities = len(filtered)
    total_visitors = filtered["TotalVisitorsClean"].sum()
    avg_visitors = filtered["TotalVisitorsClean"].mean()
    volunteer_hours = filtered["VolunteerHoursClean"].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Activities", f"{total_activities:,}")
    col2.metric("Total Visitors", f"{int(total_visitors):,}")
    col3.metric("Avg Visitors / Activity", f"{avg_visitors:.1f}")
    col4.metric("Volunteer Hours", f"{volunteer_hours:,.1f}")

    st.markdown("### Key Findings")

    if not scorecard.empty:
        top_frequency = scorecard.sort_values("ActivityCount", ascending=False).iloc[0]
        top_attendance = scorecard.sort_values("AvgVisitors", ascending=False).iloc[0]
        top_gap = scorecard.sort_values("GapScore", ascending=False).iloc[0]
        top_saturated = scorecard.sort_values("GapScore").iloc[0]

        st.write(
            f"- **{top_frequency['ActivityType']}** is the most frequently offered activity type "
            f"with **{int(top_frequency['ActivityCount'])} activities**."
        )
        st.write(
            f"- **{top_attendance['ActivityType']}** has the highest average attendance "
            f"with **{top_attendance['AvgVisitors']:.1f} visitors per activity**."
        )
        st.write(
            f"- **{top_gap['ActivityType']}** appears to be the strongest growth opportunity "
            f"based on demand relative to supply."
        )
        st.write(
            f"- **{top_saturated['ActivityType']}** may need review before adding more offerings "
            f"because supply appears high relative to demand."
        )

    st.markdown("### Stakeholder Use Case")
    st.info(
        "Use this dashboard to support decisions about which activity types to expand, "
        "which may be oversaturated, which months perform best, and where participants are coming from."
    )


# -----------------------------
# Activity Scorecard
# -----------------------------

with tabs[1]:
    st.subheader("Activity Scorecard")

    if scorecard.empty:
        st.warning("Activity type column could not be detected.")
    else:
        st.dataframe(scorecard.sort_values("AvgVisitors", ascending=False))

        st.markdown("### Average Visitors by Activity Type")
        st.bar_chart(scorecard.set_index("ActivityType")["AvgVisitors"])

        st.markdown("### Recommendation Categories")
        rec_counts = scorecard["RecommendationCategory"].value_counts()
        st.bar_chart(rec_counts)


# -----------------------------
# Opportunity Matrix
# -----------------------------

with tabs[2]:
    st.subheader("Opportunity Matrix")

    st.markdown("""
    This section compares **supply** and **demand**.

    - **Supply** = how often the activity type is offered
    - **Demand** = average visitors per activity
    - **Growth Opportunity** = high demand, lower supply
    - **Possible Oversaturation** = high supply, lower demand
    """)

    if scorecard.empty:
        st.warning("Activity scorecard could not be created.")
    else:
        matrix = scorecard.sort_values("GapScore", ascending=False)

        st.dataframe(matrix)

        st.markdown("### Highest Growth Opportunities")
        growth = matrix[matrix["RecommendationCategory"] == "Growth Opportunity"]

        if growth.empty:
            st.info("No strong growth opportunities detected with the current filters.")
        else:
            for _, row in growth.head(5).iterrows():
                st.success(
                    f"Consider testing or expanding **{row['ActivityType']}**. "
                    f"It averages **{row['AvgVisitors']:.1f} visitors per activity** "
                    f"across **{int(row['ActivityCount'])} activities**."
                )

        st.markdown("### Possible Oversaturation")
        saturated = matrix[matrix["RecommendationCategory"] == "Possible Oversaturation"]

        if saturated.empty:
            st.info("No major oversaturation detected with the current filters.")
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

    if "Month" in filtered.columns and activity_type_col:
        monthly = (
            filtered.groupby(["MonthNum", "Month", activity_type_col])
            .agg(
                ActivityCount=(activity_type_col, "count"),
                AvgVisitors=("TotalVisitorsClean", "mean"),
                TotalVisitors=("TotalVisitorsClean", "sum")
            )
            .reset_index()
            .rename(columns={activity_type_col: "ActivityType"})
            .sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])
        )

        best_by_month = monthly.groupby(["MonthNum", "Month"]).head(3)

        st.markdown("### Top Activity Types by Month")
        st.dataframe(best_by_month)

        selected_month = st.selectbox(
            "Choose a month",
            best_by_month["Month"].dropna().unique()
        )

        month_recs = best_by_month[best_by_month["Month"] == selected_month]

        st.markdown(f"### Recommendations for {selected_month}")
        for _, row in month_recs.iterrows():
            st.info(
                f"**{row['ActivityType']}** performs well in **{selected_month}**, "
                f"averaging **{row['AvgVisitors']:.1f} visitors per activity**."
            )
    else:
        st.info("Monthly recommendations require a date column and activity type column.")

    if "DayOfWeek" in filtered.columns:
        day_summary = (
            filtered.groupby("DayOfWeek")
            .agg(
                ActivityCount=("DayOfWeek", "count"),
                AvgVisitors=("TotalVisitorsClean", "mean"),
                TotalVisitors=("TotalVisitorsClean", "sum")
            )
            .sort_values("AvgVisitors", ascending=False)
        )

        st.markdown("### Best Days of Week")
        st.dataframe(day_summary)
        st.bar_chart(day_summary["AvgVisitors"])


# -----------------------------
# Attendance & No-Shows
# -----------------------------

with tabs[4]:
    st.subheader("Attendance and No-Show Analysis")

    if registered_col and noshow_col and activity_type_col:
        attendance = (
            filtered.groupby(activity_type_col)
            .agg(
                Registered=(registered_col, "sum"),
                NoShows=(noshow_col, "sum"),
                ActualVisitors=("ActualVisitors", "sum"),
                AvgAttendanceRate=("AttendanceRate", "mean"),
                AvgNoShowRate=("NoShowRate", "mean")
            )
            .reset_index()
            .rename(columns={activity_type_col: "ActivityType"})
            .sort_values("AvgNoShowRate", ascending=False)
        )

        st.dataframe(attendance)

        st.markdown("### No-Show Rate by Activity Type")
        st.bar_chart(attendance.set_index("ActivityType")["AvgNoShowRate"])

        st.markdown("### No-Show Recommendations")

        for _, row in attendance.head(5).iterrows():
            if pd.notna(row["AvgNoShowRate"]):
                st.warning(
                    f"**{row['ActivityType']}** has an average no-show rate of "
                    f"**{row['AvgNoShowRate']:.1%}**. Consider reminders, waitlists, "
                    f"or adjusted overbooking assumptions."
                )
    else:
        st.info(
            "No-show analysis requires detected registered and no-show columns. "
            "Check the Detected Columns panel in the sidebar."
        )


# -----------------------------
# Volunteer Analysis
# -----------------------------

with tabs[5]:
    st.subheader("Volunteer Effectiveness")

    if activity_type_col:
        volunteer_summary = (
            filtered.groupby(activity_type_col)
            .agg(
                ActivityCount=(activity_type_col, "count"),
                TotalVisitors=("TotalVisitorsClean", "sum"),
                AvgVisitors=("TotalVisitorsClean", "mean"),
                VolunteerHours=("VolunteerHoursClean", "sum"),
                AvgVolunteerHours=("VolunteerHoursClean", "mean")
            )
            .reset_index()
            .rename(columns={activity_type_col: "ActivityType"})
        )

        volunteer_summary["VisitorsPerVolunteerHour"] = np.where(
            volunteer_summary["VolunteerHours"] > 0,
            volunteer_summary["TotalVisitors"] / volunteer_summary["VolunteerHours"],
            np.nan
        )

        st.dataframe(volunteer_summary.sort_values("VolunteerHours", ascending=False))

        st.markdown("### Volunteer Hours by Activity Type")
        st.bar_chart(volunteer_summary.set_index("ActivityType")["VolunteerHours"])

        st.markdown("### Volunteer Planning Recommendation")
        best_efficiency = volunteer_summary.sort_values(
            "VisitorsPerVolunteerHour", ascending=False
        ).head(5)

        for _, row in best_efficiency.iterrows():
            if pd.notna(row["VisitorsPerVolunteerHour"]):
                st.success(
                    f"**{row['ActivityType']}** reaches about "
                    f"**{row['VisitorsPerVolunteerHour']:.1f} visitors per volunteer hour**."
                )


# -----------------------------
# Geography
# -----------------------------

with tabs[6]:
    st.subheader("Geographic Participant Analysis")

    st.caption(
        "This section uses public signup data. If only ZIP codes are available, "
        "the dashboard estimates city-level origins from a built-in ZIP prefix lookup."
    )

    public_geo = public.copy()

    if zip_col_public:
        public_geo[zip_col_public] = (
            public_geo[zip_col_public]
            .astype(str)
            .str.extract(r"(\d{5})")[0]
        )

        zip_city_prefix = {
            "900": "Los Angeles Area",
            "901": "Los Angeles Area",
            "902": "West LA / South Bay Area",
            "903": "Inglewood Area",
            "904": "Santa Monica Area",
            "905": "Torrance Area",
            "906": "Southeast LA / North OC Area",
            "907": "Long Beach / South Bay Area",
            "908": "Long Beach Area",
            "910": "Pasadena / San Gabriel Valley",
            "911": "Pasadena Area",
            "912": "Glendale Area",
            "913": "San Fernando Valley",
            "914": "San Fernando Valley",
            "915": "Burbank Area",
            "916": "North Hollywood Area",
            "917": "San Gabriel Valley / Inland Empire",
            "918": "Alhambra Area",
            "919": "San Diego County",
            "920": "San Diego County",
            "921": "San Diego Area",
            "922": "Coachella Valley / Desert Area",
            "923": "San Bernardino County",
            "924": "San Bernardino Area",
            "925": "Riverside County",
            "926": "Orange County",
            "927": "Santa Ana / Central OC",
            "928": "North Orange County",
            "930": "Ventura County",
            "931": "Santa Barbara Area",
            "932": "Central California",
            "933": "Bakersfield Area",
            "934": "Central Coast",
            "935": "Antelope Valley",
            "936": "Central California",
            "937": "Fresno Area",
            "939": "Monterey County",
            "940": "Bay Area",
            "941": "San Francisco",
            "945": "East Bay Area",
            "946": "Oakland Area",
            "947": "Berkeley Area",
            "950": "Santa Cruz / South Bay Area",
            "951": "San Jose Area",
        }

        public_geo["ZipPrefix"] = public_geo[zip_col_public].str[:3]
        public_geo["EstimatedCityArea"] = public_geo["ZipPrefix"].map(zip_city_prefix)

        st.markdown("### Top ZIP Codes")
        zip_summary = public_geo[zip_col_public].value_counts().head(20)
        st.dataframe(zip_summary)
        st.bar_chart(zip_summary)

        st.markdown("### Estimated City / Regional Areas From ZIP Codes")
        area_summary = public_geo["EstimatedCityArea"].value_counts().head(20)
        st.dataframe(area_summary)
        st.bar_chart(area_summary)

    if city_col_public:
        st.markdown("### Actual Cities From Public Signup Data")
        city_summary = public_geo[city_col_public].value_counts().head(20)
        st.dataframe(city_summary)
        st.bar_chart(city_summary)

    if state_col_public:
        st.markdown("### States From Public Signup Data")
        state_summary = public_geo[state_col_public].value_counts().head(20)
        st.dataframe(state_summary)

    if not zip_col_public and not city_col_public and not state_col_public:
        st.info("No ZIP, city, or state columns detected in public signup data.")


# -----------------------------
# Raw Data
# -----------------------------

with tabs[7]:
    st.subheader("Filtered Activity Data")
    st.dataframe(filtered)

    st.markdown("### Public Signup Data")
    st.dataframe(public.head(100))

    st.markdown("### Volunteer Signup Data")
    st.dataframe(volunteers.head(100))

    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Filtered Activity Data",
        data=csv,
        file_name="filtered_activity_data.csv",
        mime="text/csv"
    )
