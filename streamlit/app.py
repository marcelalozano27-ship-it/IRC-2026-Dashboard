import html
import re

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="IRC Activity Planning Dashboard",
    layout="wide"
)

SHARED_PASSWORD = "lgo2026"


# --------------------------------------------------
# Password protection
# --------------------------------------------------

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("IRC Activity Planning Dashboard")
    st.caption("Please enter the shared password to access the dashboard.")

    password = st.text_input("Password", type="password")

    if password == SHARED_PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()
    elif password:
        st.error("Incorrect password")

    return False


if not check_password():
    st.stop()


# --------------------------------------------------
# Load data
# --------------------------------------------------

@st.cache_data
def load_data():
    activities = pd.read_csv("data/activity_level.csv")

    try:
        public = pd.read_csv("data/public_signups.csv")
    except FileNotFoundError:
        public = pd.DataFrame()

    try:
        volunteers = pd.read_csv("data/volunteer_signups.csv")
    except FileNotFoundError:
        volunteers = pd.DataFrame()

    return activities, public, volunteers


activities, public, volunteers = load_data()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def ensure_column(df, column, default_value):
    if column not in df.columns:
        df[column] = default_value
    return df


def pct(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def clean_fig(fig, height=500):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=100),
        legend_title_text="",
    )
    return fig


def normalize_activity_text(name):
    text = html.unescape(str(name)).lower()

    replacements = {
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "â€“": "-",
        "â€”": "-",
        "&amp;": "&",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"(?i)cancelled:|canceled:", "", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\b\d{1,2}\s*(am|pm)\b", "", text)
    text = re.sub(r"\b20\d{2}\b", "", text)
    text = re.sub(r"\brth-[a-z0-9\-]+", "", text)
    text = re.sub(r"\brtn-[a-z0-9\-]+", "", text)
    text = re.sub(r"\bpef-[a-z0-9\-]+", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9\s&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def create_program_group(name):
    text = normalize_activity_text(name)

    if not text:
        return "Other Program"

    # Access days and large special events
    if "wilderness access day" in text:
        return "Wilderness Access Day"

    if "friends family day" in text or "friends and family day" in text:
        return "Friends & Family Day"

    if "volunteer friends" in text or "volunteer partner" in text or "irvine ranch conservancy volunteer" in text:
        return "IRC Volunteer Events"

       # Hiking and fitness
    if "hike" in text or "hiking" in text:
        return "Hikes"

    if "trail running" in text:
        return "Trail Running"

    if "yoga" in text:
        return "Yoga and Wellness"
        
    # Biking and equestrian
    if "mountain bike clinic" in text or "bike clinic" in text:
        return "Mountain Bike Clinics"

    if "mountain bike ride" in text or "bike ride" in text:
        return "Mountain Bike Rides"

    if "equestrian" in text or "training ride" in text:
        return "Equestrian Programs"

    # Stewardship and restoration
    if "native seed farm" in text or "native seed processing" in text or "growing together" in text:
        return "Native Seed Farm"

    if "native plant nursery" in text or "plant nursery" in text:
        return "Native Plant Nursery"

    if "invasive" in text or "restoration" in text or "weed" in text or "open space invaders" in text:
        return "Habitat Restoration"

    if "watering" in text:
        return "Watering and Plant Care"

    if "trail crew" in text:
        return "Trail Crew"

    # Interpretive, wildlife, and community science
    if "raptor nest" in text or "raptor monitoring" in text:
        return "Raptor Nest Monitoring"

    if "wildlife awareness" in text or "wildlife" in text:
        return "Wildlife Awareness"

    if "bird" in text:
        return "Birding"

    if "bugs" in text or "butterflies" in text:
        return "Bugs and Butterflies"

    if "science camera" in text or "camera pick up" in text:
        return "Community Science"

    if "visit nature in your backyard" in text:
        return "Nature in Your Backyard"

    if "exploration day" in text:
        return "Exploration Days"

    if "fire watch" in text:
        return "Fire Watch"

    # Fallback cleanup for less common activities
    fallback = html.unescape(str(name))
    fallback = re.sub(r"(?i)cancelled:|canceled:", "", fallback)
    fallback = re.sub(r"\*+", "", fallback)
    fallback = re.sub(r"\b\d{1,2}\s*(AM|PM|am|pm)\b", "", fallback)
    fallback = re.sub(r"\b20\d{2}\b", "", fallback)
    fallback = re.sub(r"\([^)]*\)", "", fallback)
    fallback = fallback.split(":")[0]
    fallback = fallback.strip()

    if len(fallback) > 45:
        fallback = fallback[:45].rsplit(" ", 1)[0]

    return fallback if fallback else "Other Program"


def build_scorecard(df, group_col="ProgramGroup"):
    if df.empty:
        return pd.DataFrame()

    scorecard = (
        df.groupby(group_col)
        .agg(
            ActivityCount=("ActivityID", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            MedianVisitors=("TotalVisitors", "median"),
            Registered=("VisitorsRegistered", "sum"),
            NoShows=("VisitorsNoShow", "sum"),
            WalkUps=("VisitorsWalkUp", "sum"),
            Children=("VisitorsChildren", "sum"),
            IrvineResidents=("VisitorsRegisteredIrvineResident", "sum"),
            NonResidents=("VisitorsRegisteredIrvineNonResident", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            StaffHours=("StaffHours", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean"),
            AvgFillRate=("FillRate", "mean"),
            VisitorsPerVolunteerHour=("VisitorsPerVolunteerHour", "mean"),
            VisitorsPerStaffHour=("VisitorsPerStaffHour", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "ProgramGroup"})
    )

    scorecard["SupplyScore"] = scorecard["ActivityCount"] / scorecard["ActivityCount"].max()
    scorecard["DemandScore"] = scorecard["AvgVisitors"] / scorecard["AvgVisitors"].max()
    scorecard["GapScore"] = scorecard["DemandScore"] - scorecard["SupplyScore"]

    scorecard["ResidentShare"] = np.where(
        scorecard["IrvineResidents"] + scorecard["NonResidents"] > 0,
        scorecard["IrvineResidents"] / (scorecard["IrvineResidents"] + scorecard["NonResidents"]),
        np.nan
    )

    scorecard["ProgramHealthScore"] = (
        scorecard["DemandScore"].fillna(0) * 0.30
        + scorecard["AvgFillRate"].fillna(scorecard["AvgFillRate"].median()) * 0.25
        + (1 - scorecard["AvgNoShowRate"].fillna(scorecard["AvgNoShowRate"].median())) * 0.20
        + scorecard["AvgAttendanceRate"].fillna(scorecard["AvgAttendanceRate"].median()) * 0.15
        + np.minimum(scorecard["ActivityCount"] / 10, 1) * 0.10
    )

    scorecard["RecommendationCategory"] = np.select(
        [
            scorecard["GapScore"] >= 0.20,
            scorecard["GapScore"] <= -0.20,
            (scorecard["DemandScore"] >= scorecard["DemandScore"].median())
            & (scorecard["SupplyScore"] >= scorecard["SupplyScore"].median()),
        ],
        [
            "Expansion Opportunity",
            "Review Supply",
            "Core Program",
        ],
        default="Monitor"
    )

    return scorecard.sort_values("ProgramHealthScore", ascending=False)


# --------------------------------------------------
# Data cleaning and feature engineering
# --------------------------------------------------

required_columns = {
    "ActivityID": "",
    "Date": "",
    "ActivityType": "Unknown",
    "ActivitySubType": "Unknown",
    "ActivityName": "Unknown Activity",
    "Organization": "Unknown",
    "ActivityStatus": "Unknown",
    "CancelReason": "",
    "cancel_reason_label": "",
    "Volunteers": 0,
    "VolunteerHours": 0,
    "Staff": 0,
    "StaffHours": 0,
    "VisitorsRegistered": 0,
    "VisitorsNoShow": 0,
    "VisitorsWalkUp": 0,
    "VisitorsChildren": 0,
    "VisitorsRegisteredIrvineResident": 0,
    "VisitorsRegisteredIrvineNonResident": 0,
    "TotalVisitors": 0,
    "TotalGuests": 0,
    "public_visitor_slots": 0,
    "Duration": 0,
    "IsIrcLed": "",
    "IsPrivate": "",
}

for col, default in required_columns.items():
    activities = ensure_column(activities, col, default)

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")
activities["Year"] = activities["Date"].dt.year
activities["Month"] = activities["Date"].dt.month_name()
activities["MonthNum"] = activities["Date"].dt.month
activities["DayOfWeek"] = activities["Date"].dt.day_name()

numeric_cols = [
    "Volunteers",
    "VolunteerHours",
    "Staff",
    "StaffHours",
    "VisitorsRegistered",
    "VisitorsNoShow",
    "VisitorsWalkUp",
    "VisitorsChildren",
    "VisitorsRegisteredIrvineResident",
    "VisitorsRegisteredIrvineNonResident",
    "TotalVisitors",
    "TotalGuests",
    "public_visitor_slots",
    "Duration",
]

for col in numeric_cols:
    activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

for col in ["ActivityType", "ActivitySubType", "ActivityName", "Organization", "ActivityStatus"]:
    activities[col] = activities[col].astype(str).replace("nan", "Unknown").fillna("Unknown")

# Remove cancelled activities before building program groups
cancelled_mask = (
    activities["ActivityName"].str.contains("cancelled|canceled", case=False, na=False)
    | activities["ActivityStatus"].str.contains("cancelled|canceled", case=False, na=False)
    | activities["CancelReason"].astype(str).str.strip().ne("")
    | activities["cancel_reason_label"].astype(str).str.strip().ne("")
)

activities = activities[~cancelled_mask].copy()
activities["ProgramGroup"] = activities["ActivityName"].apply(create_program_group)

activities["ActualVisitors"] = (
    activities["VisitorsRegistered"] - activities["VisitorsNoShow"]
).clip(lower=0)

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

activities["VisitorsPerVolunteerHour"] = np.where(
    activities["VolunteerHours"] > 0,
    activities["TotalVisitors"] / activities["VolunteerHours"],
    np.nan
)

activities["VisitorsPerStaffHour"] = np.where(
    activities["StaffHours"] > 0,
    activities["TotalVisitors"] / activities["StaffHours"],
    np.nan
)


# Public signup cleaning
if not public.empty and "ActivityID" in public.columns:
    if "state" in public.columns:
        public["state_clean"] = public["state"].astype(str).str.strip().str.upper()

        state_map = {
            "CA": "California",
            "CA.": "California",
            "CALIFORNIA": "California",
            "CALIF": "California",
            "AZ": "Arizona",
            "ARIZONA": "Arizona",
            "TX": "Texas",
            "TEXAS": "Texas",
            "NV": "Nevada",
            "NEVADA": "Nevada",
            "CO": "Colorado",
            "COLORADO": "Colorado",
            "FL": "Florida",
            "FLORIDA": "Florida",
        }

        public["state_clean"] = (
            public["state_clean"]
            .map(state_map)
            .fillna(public["state_clean"].str.title())
        )
    else:
        public["state_clean"] = "Unknown"


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("IRC Activity Planning Dashboard")
st.caption("Sprint 1 prototype for evidence-based activity planning and program recommendations.")

st.markdown("""
IRC has collected over a decade of activity, participant, and volunteer data through LetsGoOutside.org. This dashboard is designed as a **decision-support tool**, not simply a reporting tool. Because activity names are often similar but not identical, the dashboard groups related activity names into broader **Program Groups** to support clearer planning decisions.
""")


# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

st.sidebar.header("Filters")
st.sidebar.caption("Filters apply across all tabs.")

filtered = activities.copy()

years = sorted(filtered["Year"].dropna().astype(int).unique())
selected_years = st.sidebar.multiselect("Year", years, default=years)
filtered = filtered[filtered["Year"].isin(selected_years)]

activity_types = sorted(filtered["ActivityType"].dropna().unique())
selected_activity_types = st.sidebar.multiselect("Activity Type", activity_types, default=activity_types)
filtered = filtered[filtered["ActivityType"].isin(selected_activity_types)]

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

organizations = sorted(filtered["Organization"].dropna().unique())
selected_orgs = st.sidebar.multiselect("Organization", organizations, default=organizations)
filtered = filtered[filtered["Organization"].isin(selected_orgs)]

children_filter = st.sidebar.selectbox("Children Included?", ["All", "Yes", "No"])

if children_filter == "Yes":
    filtered = filtered[filtered["VisitorsChildren"] > 0]
elif children_filter == "No":
    filtered = filtered[filtered["VisitorsChildren"] == 0]

min_recurring_count = st.sidebar.slider(
    "Minimum Activities for Program Rankings",
    min_value=1,
    max_value=10,
    value=3,
    help="Use this to reduce one-time events in ranking tables and charts."
)

if not public.empty and "ActivityID" in public.columns:
    public_filtered = public[public["ActivityID"].isin(filtered["ActivityID"])].copy()

    states = sorted(public_filtered["state_clean"].dropna().unique())

    if states:
        selected_states = st.sidebar.multiselect("Participant State", states, default=states)
        public_filtered = public_filtered[public_filtered["state_clean"].isin(selected_states)]
        filtered = filtered[filtered["ActivityID"].isin(public_filtered["ActivityID"])]
else:
    public_filtered = pd.DataFrame()


scorecard = build_scorecard(filtered)
recurring_scorecard = scorecard[scorecard["ActivityCount"] >= min_recurring_count].copy()

if recurring_scorecard.empty:
    recurring_scorecard = scorecard.copy()


# --------------------------------------------------
# Tabs
# --------------------------------------------------

tabs = st.tabs([
    "Overview",
    "Program Explorer",
    "Participation Drivers",
    "Timing & Trends",
    "Growth Opportunities",
    "Resource & Audience Insights",
    "Operations"
])


# --------------------------------------------------
# Overview
# --------------------------------------------------

with tabs[0]:
    st.header("Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Activities", f"{len(filtered):,}")
    col2.metric("Total Visitors", f"{filtered['TotalVisitors'].sum():,.0f}")
    col3.metric(
        "Avg Visitors / Activity",
        f"{filtered['TotalVisitors'].mean():.1f}" if len(filtered) else "N/A"
    )
    col4.metric("Program Groups", f"{filtered['ProgramGroup'].nunique():,}")

    st.subheader("Executive Recommendations")

    if scorecard.empty:
        st.warning("No data available for the selected filters.")
    else:
        growth = recurring_scorecard[
            recurring_scorecard["RecommendationCategory"] == "Expansion Opportunity"
        ].sort_values("GapScore", ascending=False).head(1)

        review = recurring_scorecard[
            recurring_scorecard["RecommendationCategory"] == "Review Supply"
        ].sort_values("GapScore", ascending=True).head(1)

        core = recurring_scorecard[
            recurring_scorecard["RecommendationCategory"] == "Core Program"
        ].sort_values("ProgramHealthScore", ascending=False).head(1)

        c1, c2, c3 = st.columns(3)

        with c1:
            if not growth.empty:
                row = growth.iloc[0]
                st.success(
                    f"**Expansion Opportunity**\n\n"
                    f"Consider evaluating whether **{row['ProgramGroup']}** should be expanded. "
                    f"It has stronger demand relative to how often it is currently offered."
                )
            else:
                st.info("No clear expansion opportunity detected under the current filters.")

        with c2:
            if not review.empty:
                row = review.iloc[0]
                st.warning(
                    f"**Review Supply**\n\n"
                    f"Review **{row['ProgramGroup']}** before adding more offerings. "
                    f"It has higher supply relative to its average participation."
                )
            else:
                st.info("No clear supply concern detected under the current filters.")

        with c3:
            if not core.empty:
                row = core.iloc[0]
                st.info(
                    f"**Protect Core Program**\n\n"
                    f"**{row['ProgramGroup']}** appears to be a core program because it combines "
                    f"strong demand with consistent activity supply."
                )
            else:
                st.info("Core programs will appear here once enough recurring data is available.")

    st.subheader("Top Recurring Program Groups")

    if not recurring_scorecard.empty:
        table = recurring_scorecard.head(10).copy()

        table = table[[
            "ProgramGroup",
            "RecommendationCategory",
            "ActivityCount",
            "TotalVisitors",
            "AvgVisitors",
            "AvgFillRate",
            "AvgNoShowRate",
            "ProgramHealthScore",
        ]]

        table = table.rename(columns={
            "ProgramGroup": "Program Group",
            "RecommendationCategory": "Recommendation",
            "ActivityCount": "Activities",
            "TotalVisitors": "Total Visitors",
            "AvgVisitors": "Avg Visitors",
            "AvgFillRate": "Fill Rate",
            "AvgNoShowRate": "No Show Rate",
            "ProgramHealthScore": "Health Score",
        })

        table["Avg Visitors"] = table["Avg Visitors"].round(1)
        table["Fill Rate"] = table["Fill Rate"].map(pct)
        table["No Show Rate"] = table["No Show Rate"].map(pct)
        table["Health Score"] = table["Health Score"].round(2)

        st.dataframe(table, use_container_width=True, hide_index=True)

    st.markdown("---")

    st.subheader("Sprint 1 Assumptions & Next Steps")

    st.markdown("""
    This prototype is intended to establish the analytical direction of the project and gather feedback from IRC before final dashboard development.

    **Current assumptions**
    - Activity names need to be grouped into broader program groups because similar activities may be named differently.
    - Program success should consider participation, fill rate, no-show behavior, resource use, and activity supply.
    - High participation with low supply may indicate expansion opportunity.
    - High supply with lower participation may indicate programs to review before additional investment.

    **Planned Sprint 2 enhancements**
    - Validate program groupings with IRC.
    - Refine recommendation logic using stakeholder feedback.
    - Improve geographic participation analysis.
    - Add clearer program-level planning recommendations.
    """)


# --------------------------------------------------
# Program Explorer
# --------------------------------------------------

with tabs[1]:
    st.header("Program Explorer")
    st.caption("Explore recurring program groups created from similar activity names.")

    if scorecard.empty:
        st.warning("No program data available for selected filters.")
    else:
        program_options = sorted(scorecard["ProgramGroup"].dropna().unique())
        selected_program = st.selectbox("Select Program Group", program_options)

        program_df = filtered[filtered["ProgramGroup"] == selected_program].copy()
        program_card = build_scorecard(program_df).iloc[0]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Activities", f"{int(program_card['ActivityCount']):,}")
        c2.metric("Total Visitors", f"{program_card['TotalVisitors']:,.0f}")
        c3.metric("Avg Visitors", f"{program_card['AvgVisitors']:.1f}")
        c4.metric("Recommendation", program_card["RecommendationCategory"])

        c5, c6, c7, c8 = st.columns(4)

        c5.metric("Fill Rate", pct(program_card["AvgFillRate"]))
        c6.metric("No Show Rate", pct(program_card["AvgNoShowRate"]))
        c7.metric("Volunteer Hours", f"{program_card['VolunteerHours']:,.1f}")
        c8.metric("Health Score", f"{program_card['ProgramHealthScore']:.2f}")

        st.subheader("Activity Names Included")

        names = (
            program_df.groupby("ActivityName")
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                FillRate=("FillRate", "mean"),
                NoShowRate=("NoShowRate", "mean"),
            )
            .reset_index()
            .sort_values(["Activities", "TotalVisitors"], ascending=False)
        )

        names = names.rename(columns={
            "ActivityName": "Activity Name",
            "TotalVisitors": "Total Visitors",
            "AvgVisitors": "Avg Visitors",
            "FillRate": "Fill Rate",
            "NoShowRate": "No Show Rate",
        })

        names["Avg Visitors"] = names["Avg Visitors"].round(1)
        names["Fill Rate"] = names["Fill Rate"].map(pct)
        names["No Show Rate"] = names["No Show Rate"].map(pct)

        st.dataframe(names.head(30), use_container_width=True, hide_index=True)

        st.subheader("Program Trend")

        trend = (
            program_df.groupby("Year")
            .agg(
                TotalVisitors=("TotalVisitors", "sum"),
                Activities=("ActivityID", "count"),
                AvgVisitors=("TotalVisitors", "mean"),
            )
            .reset_index()
            .sort_values("Year")
        )

        if not trend.empty:
            fig = px.line(
                trend,
                x="Year",
                y="TotalVisitors",
                markers=True,
                title=f"{selected_program}: Total Visitors by Year",
            )
            st.plotly_chart(clean_fig(fig, 430), use_container_width=True)


# --------------------------------------------------
# Participation Drivers
# --------------------------------------------------

with tabs[2]:
    st.header("Participation Drivers")
    st.caption("Identify which recurring program groups drive participation and which show capacity pressure.")

    if recurring_scorecard.empty:
        st.warning("No data available.")
    else:
        top_total = recurring_scorecard.sort_values("TotalVisitors", ascending=False).head(15)

        fig = px.bar(
            top_total,
            x="ProgramGroup",
            y="TotalVisitors",
            color="RecommendationCategory",
            title="Top Recurring Program Groups by Total Visitors",
        )
        fig.update_xaxes(title="Program Group", tickangle=-35)
        fig.update_yaxes(title="Total Visitors")
        st.plotly_chart(clean_fig(fig), use_container_width=True)

        st.subheader("Capacity & No-Show Risk")

        quality = recurring_scorecard.dropna(subset=["AvgFillRate", "AvgNoShowRate"]).copy()

        if quality.empty:
            st.info("Not enough recurring program data available for capacity and no-show analysis.")
        else:
            quality["CapacityRisk"] = np.select(
                [
                    quality["AvgFillRate"] >= 0.90,
                    quality["AvgFillRate"] <= 0.50,
                ],
                [
                    "Near Capacity",
                    "Underfilled",
                ],
                default="Moderate"
            )

            fig = px.scatter(
                quality,
                x="AvgFillRate",
                y="AvgNoShowRate",
                size="TotalVisitors",
                color="CapacityRisk",
                hover_name="ProgramGroup",
                title="Capacity and No-Show Risk by Program Group",
                size_max=55,
            )

            fig.update_xaxes(title="Average Fill Rate", tickformat=".0%")
            fig.update_yaxes(title="Average No-Show Rate", tickformat=".0%")
            fig.add_vline(x=0.90, line_dash="dash")
            fig.add_vline(x=0.50, line_dash="dash")

            st.plotly_chart(clean_fig(fig, 530), use_container_width=True)

            st.info(
                "This view is more useful than ranking attendance rate alone because it shows whether programs are filling available capacity and whether registered participants are actually showing up."
            )


# --------------------------------------------------
# Timing & Trends
# --------------------------------------------------

with tabs[3]:
    st.header("Timing & Trends")
    st.caption("Understand when participation occurs and which time periods perform best.")

    yearly = (
        filtered.groupby("Year")
        .agg(
            TotalVisitors=("TotalVisitors", "sum"),
            Activities=("ActivityID", "count"),
            AvgVisitors=("TotalVisitors", "mean"),
        )
        .reset_index()
        .sort_values("Year")
    )

    if yearly.empty:
        st.warning("No timing data available.")
    else:
        fig = px.line(
            yearly,
            x="Year",
            y="TotalVisitors",
            markers=True,
            title="Total Visitors by Year",
        )
        st.plotly_chart(clean_fig(fig, 430), use_container_width=True)

        heat = (
            filtered.groupby(["Month", "DayOfWeek"])
            .agg(AvgVisitors=("TotalVisitors", "mean"))
            .reset_index()
        )

        heat["Month"] = pd.Categorical(heat["Month"], categories=month_order, ordered=True)
        heat["DayOfWeek"] = pd.Categorical(heat["DayOfWeek"], categories=days_order, ordered=True)

        pivot = (
            heat.pivot(index="Month", columns="DayOfWeek", values="AvgVisitors")
            .reindex(month_order)
        )

        st.subheader("Attendance Heatmap")

        fig = px.imshow(
            pivot,
            text_auto=".1f",
            aspect="auto",
            title="Average Visitors by Month and Day of Week",
        )
        st.plotly_chart(clean_fig(fig, 560), use_container_width=True)

        month_summary = (
            filtered.groupby("Month")
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
            )
            .reset_index()
        )

        month_summary["Month"] = pd.Categorical(
            month_summary["Month"],
            categories=month_order,
            ordered=True
        )

        month_summary = month_summary.sort_values("Month")

        fig = px.bar(
            month_summary,
            x="Month",
            y="AvgVisitors",
            title="Average Visitors by Month",
        )
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(clean_fig(fig, 430), use_container_width=True)


# --------------------------------------------------
# Growth Opportunities
# --------------------------------------------------

with tabs[4]:
    st.header("Growth Opportunities")
    st.caption("Compare activity supply with participant demand to identify expansion or review opportunities.")

    if recurring_scorecard.empty:
        st.warning("No data available.")
    else:
        st.markdown("""
        **How to read this chart**
        - High demand and low supply = possible expansion opportunity
        - High supply and low demand = review before adding more offerings
        - High supply and high demand = core program
        - Low supply and low demand = monitor
        """)

        fig = px.scatter(
            recurring_scorecard,
            x="SupplyScore",
            y="DemandScore",
            size="TotalVisitors",
            color="RecommendationCategory",
            hover_name="ProgramGroup",
            title="Supply vs Demand Opportunity Matrix",
            size_max=60,
        )

        fig.update_xaxes(title="Supply Score: How often the program is offered")
        fig.update_yaxes(title="Demand Score: Average visitors per activity")

        fig.add_hline(y=recurring_scorecard["DemandScore"].median(), line_dash="dash")
        fig.add_vline(x=recurring_scorecard["SupplyScore"].median(), line_dash="dash")

        st.plotly_chart(clean_fig(fig, 560), use_container_width=True)

        recommendation_counts = (
            recurring_scorecard["RecommendationCategory"]
            .value_counts()
            .reset_index()
        )

        recommendation_counts.columns = ["Recommendation", "Program Groups"]

        st.dataframe(recommendation_counts, use_container_width=True, hide_index=True)


# --------------------------------------------------
# Resource & Audience Insights
# --------------------------------------------------

with tabs[5]:
    st.header("Resource & Audience Insights")
    st.caption("Evaluate how programs use volunteer, staff, family, and resident participation resources.")

    if recurring_scorecard.empty:
        st.warning("No data available.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            efficiency = (
                recurring_scorecard
                .dropna(subset=["VisitorsPerVolunteerHour"])
                .sort_values("VisitorsPerVolunteerHour", ascending=False)
                .head(12)
            )

            if efficiency.empty:
                st.info("Volunteer hour efficiency is not available for the selected filters.")
            else:
                fig = px.bar(
                    efficiency,
                    x="ProgramGroup",
                    y="VisitorsPerVolunteerHour",
                    color="RecommendationCategory",
                    title="Visitors per Volunteer Hour",
                )
                fig.update_xaxes(title="Program Group", tickangle=-35)
                fig.update_yaxes(title="Visitors per Volunteer Hour")
                st.plotly_chart(clean_fig(fig), use_container_width=True)

        with c2:
            family = recurring_scorecard.sort_values("Children", ascending=False).head(12)

            fig = px.bar(
                family,
                x="ProgramGroup",
                y="Children",
                color="RecommendationCategory",
                title="Children Participation by Program Group",
            )
            fig.update_xaxes(title="Program Group", tickangle=-35)
            fig.update_yaxes(title="Children Visitors")
            st.plotly_chart(clean_fig(fig), use_container_width=True)

        st.subheader("Organization Performance")

        org = (
            filtered.groupby("Organization")
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                AvgFillRate=("FillRate", "mean"),
                AvgNoShowRate=("NoShowRate", "mean"),
                VolunteerHours=("VolunteerHours", "sum"),
                StaffHours=("StaffHours", "sum"),
            )
            .reset_index()
            .sort_values("TotalVisitors", ascending=False)
        )

        org = org.rename(columns={
            "Organization": "Organization",
            "TotalVisitors": "Total Visitors",
            "AvgVisitors": "Avg Visitors",
            "AvgFillRate": "Fill Rate",
            "AvgNoShowRate": "No Show Rate",
            "VolunteerHours": "Volunteer Hours",
            "StaffHours": "Staff Hours",
        })

        org["Avg Visitors"] = org["Avg Visitors"].round(1)
        org["Fill Rate"] = org["Fill Rate"].map(pct)
        org["No Show Rate"] = org["No Show Rate"].map(pct)

        st.dataframe(org, use_container_width=True, hide_index=True)

        if not public_filtered.empty and "state_clean" in public_filtered.columns:
            st.subheader("Participant Geography")

            state_summary = (
                public_filtered.groupby("state_clean")
                .size()
                .reset_index(name="Public Signups")
                .sort_values("Public Signups", ascending=False)
                .head(15)
            )

            fig = px.bar(
                state_summary,
                x="state_clean",
                y="Public Signups",
                title="Top Participant States",
            )
            fig.update_xaxes(title="State", tickangle=-35)
            st.plotly_chart(clean_fig(fig, 430), use_container_width=True)


# --------------------------------------------------
# Operations
# --------------------------------------------------

with tabs[6]:
    st.header("Operations")
    st.caption("Identify operational patterns such as activity status and cancellation reasons.")

    status_summary = (
        filtered.groupby("ActivityStatus")
        .agg(
            Activities=("ActivityID", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
        )
        .reset_index()
        .sort_values("Activities", ascending=False)
    )

    if status_summary.empty:
        st.warning("No operational data available.")
    else:
        fig = px.bar(
            status_summary,
            x="ActivityStatus",
            y="Activities",
            title="Activities by Status",
        )
        fig.update_xaxes(title="Activity Status", tickangle=-35)
        fig.update_yaxes(title="Number of Activities")
        st.plotly_chart(clean_fig(fig, 430), use_container_width=True)

    cancel_col = "cancel_reason_label" if "cancel_reason_label" in filtered.columns else "CancelReason"

    cancel_df = filtered[
        filtered[cancel_col].astype(str).str.strip().ne("")
        & filtered[cancel_col].astype(str).str.lower().ne("nan")
        & filtered[cancel_col].astype(str).str.lower().ne("0")
    ]

    if not cancel_df.empty:
        cancel_summary = (
            cancel_df.groupby(cancel_col)
            .agg(Activities=("ActivityID", "count"))
            .reset_index()
            .sort_values("Activities", ascending=False)
            .head(15)
        )

        fig = px.bar(
            cancel_summary,
            x=cancel_col,
            y="Activities",
            title="Top Cancellation Reasons",
        )
        fig.update_xaxes(title="Cancellation Reason", tickangle=-35)
        fig.update_yaxes(title="Number of Activities")
        st.plotly_chart(clean_fig(fig, 500), use_container_width=True)
    else:
        st.info("No cancellation reason data available for the selected filters.")
