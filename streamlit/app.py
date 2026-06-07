import re
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="IRC Activity Planning Dashboard", layout="wide")

SHARED_PASSWORD = "lgo2026"

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

def ensure_col(df, col, default=np.nan):
    if col not in df.columns:
        df[col] = default
    return df

needed_cols = [
    "ActivityID", "ActivityType", "ActivitySubType", "ActivityName", "Date",
    "Organization", "ActivityStatus", "CancelReason", "cancel_reason_label",
    "Volunteers", "VolunteerHours", "Staff", "StaffHours",
    "VisitorsRegistered", "VisitorsNoShow", "VisitorsWalkUp",
    "VisitorsChildren", "VisitorsRegisteredIrvineResident",
    "VisitorsRegisteredIrvineNonResident", "TotalVisitors",
    "public_visitor_slots", "IsIrcLed", "IsPrivate", "Duration"
]

for col in needed_cols:
    activities = ensure_col(activities, col, 0 if col not in ["ActivityType", "ActivitySubType", "ActivityName", "Date", "Organization", "ActivityStatus", "CancelReason", "cancel_reason_label"] else "")

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
    "public_visitor_slots", "Duration"
]

for col in numeric_cols:
    activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

activities["ActualVisitors"] = (activities["VisitorsRegistered"] - activities["VisitorsNoShow"]).clip(lower=0)

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

def create_program_group(name):
    text = str(name).lower()

    text = text.replace("cancelled:", "")
    text = text.replace("canceled:", "")
    text = re.sub(r"\b20\d{2}\b", "", text)
    text = re.sub(r"rth-[a-z0-9\-]+", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.strip()

    if "fitness hike" in text or "cardio hike" in text or "morning distance hike" in text:
        return "Fitness Hike"
    if "full moon hike" in text:
        return "Full Moon Hike"
    if "trail running" in text:
        return "Trail Running"
    if "equestrian" in text or "training ride" in text:
        return "Equestrian Program"
    if "native seed farm" in text or "native seed processing" in text or "growing together" in text:
        return "Native Seed Farm"
    if "invasive" in text or "restoration" in text or "weed" in text:
        return "Habitat Restoration"
    if "raptor nest" in text or "raptor monitoring" in text:
        return "Raptor Nest Monitoring"
    if "native plant nursery" in text or "plant nursery" in text:
        return "Native Plant Nursery"
    if "wildlife awareness" in text or "wildlife" in text:
        return "Wildlife Awareness"
    if "bird" in text:
        return "Birding"
    if "science camera" in text or "camera pick up" in text:
        return "Community Science"
    if "trail crew" in text:
        return "Trail Crew"
    if "yoga" in text:
        return "Yoga and Wellness"
    if "bugs" in text or "butterflies" in text:
        return "Bugs and Butterflies"
    if "watering" in text:
        return "Watering and Plant Care"

    cleaned = str(name)
    cleaned = re.sub(r"(?i)cancelled:|canceled:", "", cleaned)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\b20\d{2}\b", "", cleaned)
    cleaned = cleaned.split(":")[0]
    cleaned = cleaned.strip()

    if len(cleaned) > 45:
        cleaned = cleaned[:45].rsplit(" ", 1)[0]

    return cleaned if cleaned else "Other Program"

activities["ProgramGroup"] = activities["ActivityName"].apply(create_program_group)

if not public.empty and "ActivityID" in public.columns:
    if "state" in public.columns:
        public["state_clean"] = public["state"].astype(str).str.strip().str.upper()
        state_map = {
            "CA": "California",
            "CALIFORNIA": "California",
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
        public["state_clean"] = public["state_clean"].map(state_map).fillna(public["state_clean"].str.title())
    else:
        public["state_clean"] = "Unknown"

st.title("IRC Activity Planning Dashboard")
st.caption("Sprint 1 prototype designed to help IRC move from historical activity data to evidence-based programming decisions.")

st.markdown("""
IRC has collected over a decade of activity, participant, and volunteer data through LetsGoOutside.org. This dashboard is designed as a **decision-support tool**, not simply a reporting tool. Because IRC is still defining how historical data should support planning decisions, this prototype focuses on identifying meaningful questions, metrics, and recommendation frameworks that can guide future programming decisions.
""")

st.sidebar.header("Filters")
st.sidebar.caption("Use these controls to narrow the analysis across all tabs.")

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

if not public.empty and "ActivityID" in public.columns:
    public_filtered = public[public["ActivityID"].isin(filtered["ActivityID"])].copy()
    states = sorted(public_filtered["state_clean"].dropna().unique())
    if states:
        selected_states = st.sidebar.multiselect("Participant State", states, default=states)
        public_filtered = public_filtered[public_filtered["state_clean"].isin(selected_states)]
        filtered = filtered[filtered["ActivityID"].isin(public_filtered["ActivityID"])]
else:
    public_filtered = pd.DataFrame()

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
        scorecard["DemandScore"].fillna(0) * 0.35
        + scorecard["AvgAttendanceRate"].fillna(scorecard["AvgAttendanceRate"].median()) * 0.25
        + scorecard["AvgFillRate"].fillna(scorecard["AvgFillRate"].median()) * 0.25
        + (1 - scorecard["AvgNoShowRate"].fillna(scorecard["AvgNoShowRate"].median())) * 0.15
    )

    scorecard["RecommendationCategory"] = np.select(
        [
            scorecard["GapScore"] >= 0.20,
            scorecard["GapScore"] <= -0.20,
            (scorecard["DemandScore"] >= scorecard["DemandScore"].median())
            & (scorecard["SupplyScore"] >= scorecard["SupplyScore"].median()),
        ],
        [
            "Growth Opportunity",
            "Review Supply",
            "Core Program",
        ],
        default="Monitor",
    )

    return scorecard.sort_values("ProgramHealthScore", ascending=False)

scorecard = build_scorecard(filtered)

def pct(x):
    if pd.isna(x):
        return "N/A"
    return f"{x:.1%}"

def clean_fig(fig, height=500):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=60, b=90), legend_title_text="")
    return fig

tabs = st.tabs([
    "Overview",
    "Program Explorer",
    "Participation Drivers",
    "Timing & Trends",
    "Growth Opportunities",
    "Resource & Audience Insights",
    "Operations"
])

with tabs[0]:
    st.header("Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Activities", f"{len(filtered):,}")
    c2.metric("Total Visitors", f"{filtered['TotalVisitors'].sum():,.0f}")
    c3.metric("Avg Visitors / Activity", f"{filtered['TotalVisitors'].mean():.1f}" if len(filtered) else "N/A")
    c4.metric("Program Groups", f"{filtered['ProgramGroup'].nunique():,}")

    st.subheader("Executive Recommendations")

    if scorecard.empty:
        st.warning("No data available for the selected filters.")
    else:
        growth = scorecard[scorecard["RecommendationCategory"] == "Growth Opportunity"].head(1)
        review = scorecard[scorecard["RecommendationCategory"] == "Review Supply"].sort_values("GapScore").head(1)
        core = scorecard[scorecard["RecommendationCategory"] == "Core Program"].head(1)

        r1, r2, r3 = st.columns(3)

        with r1:
            if not growth.empty:
                row = growth.iloc[0]
                st.success(f"**Expand Carefully**\n\n{row['ProgramGroup']} shows high demand relative to current supply.")
            else:
                st.info("No clear expansion opportunity detected under current filters.")

        with r2:
            if not review.empty:
                row = review.iloc[0]
                st.warning(f"**Review Supply**\n\n{row['ProgramGroup']} has higher supply relative to average participation.")
            else:
                st.info("No clear supply concern detected under current filters.")

        with r3:
            if not core.empty:
                row = core.iloc[0]
                st.info(f"**Protect Core Programs**\n\n{row['ProgramGroup']} performs well and is offered frequently.")
            else:
                st.info("Core programs will appear here once enough activity groups are selected.")

    st.subheader("Top Program Groups by Health Score")

    if not scorecard.empty:
        display_cols = [
            "ProgramGroup", "RecommendationCategory", "ActivityCount", "TotalVisitors",
            "AvgVisitors", "AvgAttendanceRate", "AvgFillRate", "AvgNoShowRate",
            "ProgramHealthScore"
        ]

        shown = scorecard[display_cols].head(10).copy()
        shown["AvgAttendanceRate"] = shown["AvgAttendanceRate"].map(pct)
        shown["AvgFillRate"] = shown["AvgFillRate"].map(pct)
        shown["AvgNoShowRate"] = shown["AvgNoShowRate"].map(pct)
        shown["AvgVisitors"] = shown["AvgVisitors"].round(1)
        shown["ProgramHealthScore"] = shown["ProgramHealthScore"].round(2)

        st.dataframe(shown, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Sprint 1 Assumptions & Next Steps")

    st.markdown("""
    This prototype is intended to establish the analytical direction of the project and gather feedback from IRC before final dashboard development.

    **Current assumptions**
    - Program success should consider participation, attendance quality, capacity use, and activity supply.
    - Activity names need to be grouped into broader program groups because similar activities may be named differently.
    - High participation combined with low activity supply may indicate expansion opportunity.
    - High activity supply combined with lower participation may indicate programs to review before further investment.

    **Planned Sprint 2 enhancements**
    - Validate program groupings with IRC.
    - Refine recommendation logic using stakeholder feedback.
    - Add more geographic participation analysis.
    - Improve program-level recommendations and documentation.
    """)

with tabs[1]:
    st.header("Program Explorer")
    st.caption("Use this section to evaluate recurring programs created from similar activity names.")

    if scorecard.empty:
        st.warning("No programs available for selected filters.")
    else:
        program_options = sorted(scorecard["ProgramGroup"].dropna().unique())
        selected_program = st.selectbox("Select Program Group", program_options)

        program_df = filtered[filtered["ProgramGroup"] == selected_program]
        program_row = build_scorecard(program_df).iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Activities", f"{int(program_row['ActivityCount']):,}")
        c2.metric("Total Visitors", f"{program_row['TotalVisitors']:,.0f}")
        c3.metric("Avg Visitors", f"{program_row['AvgVisitors']:.1f}")
        c4.metric("Recommendation", program_row["RecommendationCategory"])

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Attendance Rate", pct(program_row["AvgAttendanceRate"]))
        c6.metric("Fill Rate", pct(program_row["AvgFillRate"]))
        c7.metric("No Show Rate", pct(program_row["AvgNoShowRate"]))
        c8.metric("Volunteer Hours", f"{program_row['VolunteerHours']:,.1f}")

        st.subheader("Activity Names Included in This Program Group")
        names = (
            program_df.groupby("ActivityName")
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
            )
            .reset_index()
            .sort_values("TotalVisitors", ascending=False)
        )
        names["AvgVisitors"] = names["AvgVisitors"].round(1)
        st.dataframe(names.head(25), use_container_width=True, hide_index=True)

        st.subheader("Program Trend")
        trend = (
            program_df.groupby("Year")
            .agg(TotalVisitors=("TotalVisitors", "sum"), Activities=("ActivityID", "count"))
            .reset_index()
            .sort_values("Year")
        )

        fig = px.line(trend, x="Year", y="TotalVisitors", markers=True, title=f"{selected_program}: Visitors by Year")
        st.plotly_chart(clean_fig(fig, 430), use_container_width=True)

with tabs[2]:
    st.header("Participation Drivers")
    st.caption("Identify which program groups generate the strongest participation.")

    if scorecard.empty:
        st.warning("No data available.")
    else:
        top_total = scorecard.sort_values("TotalVisitors", ascending=False).head(15)

        fig = px.bar(
            top_total,
            x="ProgramGroup",
            y="TotalVisitors",
            color="RecommendationCategory",
            title="Top Program Groups by Total Visitors",
        )
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(clean_fig(fig), use_container_width=True)

        st.subheader("Attendance Quality")
        quality = scorecard.sort_values("AvgAttendanceRate", ascending=False).head(15)

        fig = px.bar(
            quality,
            x="ProgramGroup",
            y="AvgAttendanceRate",
            color="RecommendationCategory",
            title="Highest Attendance Rate by Program Group",
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(clean_fig(fig), use_container_width=True)

with tabs[3]:
    st.header("Timing & Trends")
    st.caption("Understand when participation occurs and which time periods perform best.")

    yearly = (
        filtered.groupby("Year")
        .agg(TotalVisitors=("TotalVisitors", "sum"), Activities=("ActivityID", "count"))
        .reset_index()
        .sort_values("Year")
    )

    if yearly.empty:
        st.warning("No timing data available.")
    else:
        fig = px.line(yearly, x="Year", y="TotalVisitors", markers=True, title="Total Visitors by Year")
        st.plotly_chart(clean_fig(fig, 430), use_container_width=True)

        heat = (
            filtered.groupby(["Month", "DayOfWeek"])
            .agg(AvgVisitors=("TotalVisitors", "mean"))
            .reset_index()
        )

        heat["Month"] = pd.Categorical(heat["Month"], categories=month_order, ordered=True)
        heat["DayOfWeek"] = pd.Categorical(heat["DayOfWeek"], categories=days_order, ordered=True)

        pivot = heat.pivot(index="Month", columns="DayOfWeek", values="AvgVisitors").reindex(month_order)

        st.subheader("Attendance Heatmap: Month by Day of Week")
        fig = px.imshow(
            pivot,
            text_auto=".1f",
            aspect="auto",
            title="Average Visitors by Month and Day of Week",
        )
        st.plotly_chart(clean_fig(fig, 560), use_container_width=True)

with tabs[4]:
    st.header("Growth Opportunities")
    st.caption("Compare activity supply with participant demand to identify expansion or review opportunities.")

    if scorecard.empty:
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
            scorecard,
            x="SupplyScore",
            y="DemandScore",
            size="TotalVisitors",
            color="RecommendationCategory",
            hover_name="ProgramGroup",
            title="Supply vs Demand Opportunity Matrix",
            size_max=60,
        )

        fig.add_hline(y=scorecard["DemandScore"].median(), line_dash="dash")
        fig.add_vline(x=scorecard["SupplyScore"].median(), line_dash="dash")

        st.plotly_chart(clean_fig(fig, 560), use_container_width=True)

        counts = scorecard["RecommendationCategory"].value_counts().reset_index()
        counts.columns = ["Recommendation", "Program Groups"]

        st.dataframe(counts, use_container_width=True, hide_index=True)

with tabs[5]:
    st.header("Resource & Audience Insights")
    st.caption("Evaluate how programs use staff, volunteer, and audience resources.")

    if scorecard.empty:
        st.warning("No data available.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            efficiency = scorecard.dropna(subset=["VisitorsPerVolunteerHour"]).sort_values("VisitorsPerVolunteerHour", ascending=False).head(12)
            fig = px.bar(
                efficiency,
                x="ProgramGroup",
                y="VisitorsPerVolunteerHour",
                color="RecommendationCategory",
                title="Visitors per Volunteer Hour",
            )
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(clean_fig(fig), use_container_width=True)

        with c2:
            family = scorecard.sort_values("Children", ascending=False).head(12)
            fig = px.bar(
                family,
                x="ProgramGroup",
                y="Children",
                color="RecommendationCategory",
                title="Children Participation by Program Group",
            )
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(clean_fig(fig), use_container_width=True)

        st.subheader("Organization Performance")

        org = (
            filtered.groupby("Organization")
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                AvgAttendanceRate=("AttendanceRate", "mean"),
                AvgFillRate=("FillRate", "mean"),
            )
            .reset_index()
            .sort_values("TotalVisitors", ascending=False)
        )

        org["AvgVisitors"] = org["AvgVisitors"].round(1)
        org["AvgAttendanceRate"] = org["AvgAttendanceRate"].map(pct)
        org["AvgFillRate"] = org["AvgFillRate"].map(pct)

        st.dataframe(org, use_container_width=True, hide_index=True)

with tabs[6]:
    st.header("Operations")
    st.caption("Identify operational patterns such as cancellations and activity status.")

    status_summary = (
        filtered.groupby("ActivityStatus")
        .agg(Activities=("ActivityID", "count"), TotalVisitors=("TotalVisitors", "sum"))
        .reset_index()
        .sort_values("Activities", ascending=False)
    )

    fig = px.bar(
        status_summary,
        x="ActivityStatus",
        y="Activities",
        title="Activities by Status",
    )
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
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(clean_fig(fig), use_container_width=True)
    else:
        st.info("No cancellation reason data available for the selected filters.")
