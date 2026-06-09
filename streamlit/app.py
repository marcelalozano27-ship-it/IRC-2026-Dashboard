import html
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
        return "Other / Needs Review"

    if "cancelled" in text or "canceled" in text or "cancel" in text:
        return "Cancelled"

    if "trail running" in text:
        return "Trail Running"

    if "hike" in text or "hiking" in text or "trek" in text or "walk" in text:
        return "Hikes"

    if "zumba" in text:
        return "Zumba"

    if "yoga" in text or "tai chi" in text or "meditative" in text:
        return "Yoga / Wellness"

    if "mountain bike" in text or "bike ride" in text or "bike clinic" in text or "freeks ride" in text:
        return "Mountain Biking"

    if "equestrian" in text or "training ride" in text:
        return "Equestrian Programs"

    if "wilderness access day" in text:
        return "Wilderness Access Days"

    if "friends family day" in text or "friends and family day" in text:
        return "Friends & Family Days"

    if (
        "native seed farm" in text
        or "seed processing" in text
        or "seed collection" in text
        or "harvest" in text
        or "growing together" in text
        or "farm steward" in text
    ):
        return "Native Seed Farm"

    if "native plant nursery" in text or "plant nursery" in text:
        return "Native Plant Nursery"

    if "watering" in text or "water trough" in text:
        return "Watering / Plant Care"

    if "invasive" in text or "restoration" in text or "weed" in text or "open space invaders" in text:
        return "Habitat Restoration"

    if "trail crew" in text or "trail work" in text:
        return "Trail Crew / Trail Work"

    if "camera" in text or "science camera" in text:
        return "Camera Monitoring"

    if "bird" in text:
        return "Birding / Bird Monitoring"

    if "butterfly" in text or "butterflies" in text or "bugs" in text:
        return "Bugs & Butterflies"

    if "raptor" in text:
        return "Raptor Monitoring"

    if "wildlife" in text or "animal" in text or "tracking" in text:
        return "Wildlife / Animal Programs"

    if "fire watch" in text:
        return "Fire Watch"

    if "training" in text or "orientation" in text or "workshop" in text or "cpr" in text or "first aid" in text:
        return "Training / Workshops"

    if "exploration day" in text:
        return "Exploration Days"

    if "nature in your backyard" in text or "nature" in text:
        return "Nature Education"

    if "volunteer" in text:
        return "Volunteer Programs"

    if "family" in text:
        return "Family Programs"

    if "camp" in text:
        return "Camps"

    if "photography" in text or "photo" in text:
        return "Photography"

    if "star" in text or "astronomy" in text:
        return "Astronomy"

    return "Other / Needs Review"


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
            YouthParticipants=("VisitorsChildren", "sum"),
            IrvineResidents=("VisitorsRegisteredIrvineResident", "sum"),
            NonResidents=("VisitorsRegisteredIrvineNonResident", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            StaffHours=("StaffHours", "sum"),
            AvgVolunteers=("Volunteers", "mean"),
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
        ["Expansion Opportunity", "Review Supply", "Core Program"],
        default="Monitor",
    )

    return scorecard.sort_values("ProgramHealthScore", ascending=False)


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

cancelled_mask = (
    activities["ActivityName"].str.contains("cancelled|canceled|cancel", case=False, na=False)
    | activities["ActivityStatus"].str.contains("cancelled|canceled|cancel", case=False, na=False)
)

activities = activities[~cancelled_mask].copy()
activities["ProgramGroup"] = activities["ActivityName"].apply(create_program_group)

activities["ActualVisitors"] = (
    activities["VisitorsRegistered"] - activities["VisitorsNoShow"]
).clip(lower=0)

activities["AttendanceRate"] = np.where(
    activities["VisitorsRegistered"] > 0,
    activities["ActualVisitors"] / activities["VisitorsRegistered"],
    np.nan,
)

activities["NoShowRate"] = np.where(
    activities["VisitorsRegistered"] > 0,
    activities["VisitorsNoShow"] / activities["VisitorsRegistered"],
    np.nan,
)

activities["FillRate"] = np.where(
    activities["public_visitor_slots"] > 0,
    activities["VisitorsRegistered"] / activities["public_visitor_slots"],
    np.nan,
)

activities["VisitorsPerVolunteerHour"] = np.where(
    activities["VolunteerHours"] > 0,
    activities["TotalVisitors"] / activities["VolunteerHours"],
    np.nan,
)

activities["VisitorsPerStaffHour"] = np.where(
    activities["StaffHours"] > 0,
    activities["TotalVisitors"] / activities["StaffHours"],
    np.nan,
)


st.title("IRC Activity Planning Dashboard")
st.caption("Sprint 1 prototype for executive reporting and activity planning support.")

st.markdown("""
This dashboard is organized into two views: an **Executive Dashboard** to summarize IRC's overall program impact, 
and an **Activity Planning Dashboard** to help evaluate proposed activities using historical performance patterns.
""")


st.sidebar.header("Global Filters")
st.sidebar.caption("These filters apply to both dashboard tabs.")

filtered = activities.copy()

month_order = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

years = sorted(filtered["Year"].dropna().astype(int).unique())
selected_years = st.sidebar.multiselect("Year", years, default=years)
filtered = filtered[filtered["Year"].isin(selected_years)]

activity_types = sorted(filtered["ActivityType"].dropna().unique())
selected_activity_types = st.sidebar.multiselect("Activity Type", activity_types, default=activity_types)
filtered = filtered[filtered["ActivityType"].isin(selected_activity_types)]

program_groups = sorted(filtered["ProgramGroup"].dropna().unique())
selected_program_groups = st.sidebar.multiselect("Program Group", program_groups, default=program_groups)
filtered = filtered[filtered["ProgramGroup"].isin(selected_program_groups)]

with st.sidebar.expander("Additional Filters"):
    available_months = [m for m in month_order if m in filtered["Month"].dropna().unique()]
    selected_months = st.multiselect("Month", available_months, default=available_months)
    filtered = filtered[filtered["Month"].isin(selected_months)]

    available_days = [d for d in days_order if d in filtered["DayOfWeek"].dropna().unique()]
    selected_days = st.multiselect("Day of Week", available_days, default=available_days)
    filtered = filtered[filtered["DayOfWeek"].isin(selected_days)]

    family_youth_global = st.selectbox(
        "Family / Youth Participation",
        ["All", "Historically included children", "No recorded child participation"],
    )

    if family_youth_global == "Historically included children":
        filtered = filtered[filtered["VisitorsChildren"] > 0]
    elif family_youth_global == "No recorded child participation":
        filtered = filtered[filtered["VisitorsChildren"] == 0]

min_recurring_count = st.sidebar.slider(
    "Minimum Activities for Program Rankings",
    min_value=1,
    max_value=10,
    value=3,
)

scorecard = build_scorecard(filtered)
recurring_scorecard = scorecard[scorecard["ActivityCount"] >= min_recurring_count].copy()

if recurring_scorecard.empty:
    recurring_scorecard = scorecard.copy()


tabs = st.tabs(["Executive Dashboard", "Activity Planning Dashboard"])


with tabs[0]:
    st.header("Executive Dashboard")
    st.caption("High-level summary of what IRC accomplished across activities, landowners, participants, and volunteers.")

    if filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Activities", f"{len(filtered):,}")
        col2.metric("Total Visitors", f"{filtered['TotalVisitors'].sum():,.0f}")
        col3.metric("Avg Visitors / Activity", f"{filtered['TotalVisitors'].mean():.1f}")
        col4.metric("Volunteer Hours", f"{filtered['VolunteerHours'].sum():,.1f}")
        col5.metric("Youth / Family Participants", f"{filtered['VisitorsChildren'].sum():,.0f}")

        st.subheader("Executive Summary")

        top_org = (
            filtered.groupby("Organization")
            .agg(Activities=("ActivityID", "count"))
            .reset_index()
            .sort_values("Activities", ascending=False)
            .head(1)
        )

        top_program = (
            filtered.groupby("ProgramGroup")
            .agg(TotalVisitors=("TotalVisitors", "sum"))
            .reset_index()
            .sort_values("TotalVisitors", ascending=False)
            .head(1)
        )

        if not top_org.empty and not top_program.empty:
            st.info(
                f"IRC hosted **{len(filtered):,} activities** with **{filtered['TotalVisitors'].sum():,.0f} total visitors** "
                f"and **{filtered['VolunteerHours'].sum():,.1f} volunteer hours**. "
                f"The landowner/property with the most activities was **{top_org.iloc[0]['Organization']}**, "
                f"and the program group with the highest total attendance was **{top_program.iloc[0]['ProgramGroup']}**."
            )

        st.subheader("Activities by Landowner / Property")

        org_summary = (
            filtered.groupby("Organization")
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
                VolunteerHours=("VolunteerHours", "sum"),
                YouthParticipants=("VisitorsChildren", "sum"),
            )
            .reset_index()
            .sort_values("Activities", ascending=False)
        )

        fig = px.bar(
            org_summary.head(15),
            x="Organization",
            y="Activities",
            title="Number of Activities by Landowner / Property",
        )
        fig.update_xaxes(title="Landowner / Property", tickangle=-35)
        fig.update_yaxes(title="Number of Activities")
        st.plotly_chart(clean_fig(fig, 500), use_container_width=True)

        org_table = org_summary.rename(columns={
            "Organization": "Landowner / Property",
            "TotalVisitors": "Total Visitors",
            "AvgVisitors": "Avg Visitors",
            "VolunteerHours": "Volunteer Hours",
            "YouthParticipants": "Youth / Family Participants",
        }).round(1)

        st.dataframe(org_table, use_container_width=True, hide_index=True)

        st.subheader("Program Performance")

        if recurring_scorecard.empty:
            st.info("Not enough program data available for the selected filters.")
        else:
            performance = recurring_scorecard.sort_values("TotalVisitors", ascending=False).head(12)

            fig = px.bar(
                performance,
                x="ProgramGroup",
                y="TotalVisitors",
                color="RecommendationCategory",
                title="Top Program Groups by Total Visitors",
            )
            fig.update_xaxes(title="Program Group", tickangle=-35)
            fig.update_yaxes(title="Total Visitors")
            st.plotly_chart(clean_fig(fig, 500), use_container_width=True)

            program_table = recurring_scorecard[[
                "ProgramGroup",
                "RecommendationCategory",
                "ActivityCount",
                "TotalVisitors",
                "AvgVisitors",
                "VolunteerHours",
                "YouthParticipants",
                "AvgFillRate",
                "AvgNoShowRate",
            ]].copy()

            program_table = program_table.rename(columns={
                "ProgramGroup": "Program Group",
                "RecommendationCategory": "Recommendation",
                "ActivityCount": "Activities",
                "TotalVisitors": "Total Visitors",
                "AvgVisitors": "Avg Visitors",
                "VolunteerHours": "Volunteer Hours",
                "YouthParticipants": "Youth / Family Participants",
                "AvgFillRate": "Fill Rate",
                "AvgNoShowRate": "No Show Rate",
            })

            program_table["Avg Visitors"] = program_table["Avg Visitors"].round(1)
            program_table["Volunteer Hours"] = program_table["Volunteer Hours"].round(1)
            program_table["Fill Rate"] = program_table["Fill Rate"].map(pct)
            program_table["No Show Rate"] = program_table["No Show Rate"].map(pct)

            st.dataframe(program_table, use_container_width=True, hide_index=True)

        st.subheader("Draft Report Summary")

        st.markdown("""
        This section can later become an exportable leadership summary. For now, it highlights:

        - Total activities hosted
        - Total community participation
        - Volunteer engagement generated
        - Landowners/properties with the most activity
        - Program groups with the strongest performance
        - Opportunities to expand, monitor, or review programs
        """)


with tabs[1]:
    st.header("Activity Planning Dashboard")
    st.caption(
        "Use historical activity data to understand how similar activities have performed in the past."
    )

    if filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        st.subheader("Proposed Activity Scenario")

        c1, c2 = st.columns(2)

        with c1:
            planning_types = st.multiselect(
                "Activity Type",
                sorted(filtered["ActivityType"].dropna().unique()),
                default=sorted(filtered["ActivityType"].dropna().unique()),
            )

        with c2:
            planning_groups = st.multiselect(
                "Program Group",
                sorted(filtered["ProgramGroup"].dropna().unique()),
                default=sorted(filtered["ProgramGroup"].dropna().unique()),
            )

        c3, c4 = st.columns(2)

        with c3:
            planning_months = st.multiselect(
                "Month",
                [m for m in month_order if m in filtered["Month"].dropna().unique()],
                default=[m for m in month_order if m in filtered["Month"].dropna().unique()],
            )

        with c4:
            planning_days = st.multiselect(
                "Day of Week",
                [d for d in days_order if d in filtered["DayOfWeek"].dropna().unique()],
                default=[d for d in days_order if d in filtered["DayOfWeek"].dropna().unique()],
            )

        family_youth_filter = st.selectbox(
            "Family / Youth Participation",
            ["All", "Historically included children", "No recorded child participation"],
        )

        comparable = filtered.copy()

        comparable = comparable[comparable["ActivityType"].isin(planning_types)]
        comparable = comparable[comparable["ProgramGroup"].isin(planning_groups)]
        comparable = comparable[comparable["Month"].isin(planning_months)]
        comparable = comparable[comparable["DayOfWeek"].isin(planning_days)]

        if family_youth_filter == "Historically included children":
            comparable = comparable[comparable["VisitorsChildren"] > 0]
        elif family_youth_filter == "No recorded child participation":
            comparable = comparable[comparable["VisitorsChildren"] == 0]

        st.subheader("Expected Performance Based on Similar Past Activities")

        if comparable.empty:
            st.warning("No similar past activities match this scenario. Try removing one or more filters.")
        else:
            overall_avg = filtered["TotalVisitors"].mean()
            scenario_avg = comparable["TotalVisitors"].mean()

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Similar Past Activities", f"{len(comparable):,}")
            col2.metric("Avg Visitors", f"{scenario_avg:.1f}")
            col3.metric("Avg Volunteers", f"{comparable['Volunteers'].mean():.1f}")
            col4.metric("Avg Youth / Family Participants", f"{comparable['VisitorsChildren'].mean():.1f}")

            if scenario_avg > overall_avg:
                st.success(
                    f"Similar activities performed **above the dashboard average** "
                    f"({scenario_avg:.1f} vs. {overall_avg:.1f} visitors per activity)."
                )
            elif scenario_avg < overall_avg:
                st.warning(
                    f"Similar activities performed **below the dashboard average** "
                    f"({scenario_avg:.1f} vs. {overall_avg:.1f} visitors per activity)."
                )
            else:
                st.info("This scenario performs close to the dashboard average.")

            st.subheader("Best Planning Conditions")

            col1, col2 = st.columns(2)

            with col1:
                month_perf = (
                    comparable.groupby("Month")
                    .agg(
                        Activities=("ActivityID", "count"),
                        AvgVisitors=("TotalVisitors", "mean"),
                    )
                    .reset_index()
                )
                month_perf["Month"] = pd.Categorical(month_perf["Month"], categories=month_order, ordered=True)
                month_perf = month_perf.sort_values("Month")

                fig = px.bar(
                    month_perf,
                    x="Month",
                    y="AvgVisitors",
                    title="Average Visitors by Month",
                )
                fig.update_xaxes(title="Month", tickangle=-35)
                fig.update_yaxes(title="Avg Visitors")
                st.plotly_chart(clean_fig(fig, 430), use_container_width=True)

            with col2:
                day_perf = (
                    comparable.groupby("DayOfWeek")
                    .agg(
                        Activities=("ActivityID", "count"),
                        AvgVisitors=("TotalVisitors", "mean"),
                    )
                    .reset_index()
                )
                day_perf["DayOfWeek"] = pd.Categorical(day_perf["DayOfWeek"], categories=days_order, ordered=True)
                day_perf = day_perf.sort_values("DayOfWeek")

                fig = px.bar(
                    day_perf,
                    x="DayOfWeek",
                    y="AvgVisitors",
                    title="Average Visitors by Day of Week",
                )
                fig.update_xaxes(title="Day of Week", tickangle=-35)
                fig.update_yaxes(title="Avg Visitors")
                st.plotly_chart(clean_fig(fig, 430), use_container_width=True)

            st.subheader("Landowner / Property Performance")

            property_perf = (
                comparable.groupby("Organization")
                .agg(
                    Activities=("ActivityID", "count"),
                    AvgVisitors=("TotalVisitors", "mean"),
                    TotalVisitors=("TotalVisitors", "sum"),
                    AvgVolunteers=("Volunteers", "mean"),
                    YouthParticipants=("VisitorsChildren", "sum"),
                )
                .reset_index()
                .sort_values("AvgVisitors", ascending=False)
                .head(15)
            )

            fig = px.bar(
                property_perf,
                x="Organization",
                y="AvgVisitors",
                title="Average Visitors by Landowner / Property",
            )
            fig.update_xaxes(title="Landowner / Property", tickangle=-35)
            fig.update_yaxes(title="Avg Visitors")
            st.plotly_chart(clean_fig(fig, 500), use_container_width=True)

            st.dataframe(
                property_perf.rename(columns={
                    "Organization": "Landowner / Property",
                    "AvgVisitors": "Avg Visitors",
                    "TotalVisitors": "Total Visitors",
                    "AvgVolunteers": "Avg Volunteers",
                    "YouthParticipants": "Youth / Family Participants",
                }).round(1),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Similar Past Activities")

            similar_table = comparable[[
                "Date",
                "ActivityName",
                "ActivityType",
                "ProgramGroup",
                "Organization",
                "DayOfWeek",
                "Month",
                "TotalVisitors",
                "VisitorsChildren",
                "Volunteers",
                "VolunteerHours",
            ]].copy()

            similar_table = similar_table.sort_values("TotalVisitors", ascending=False)

            similar_table = similar_table.rename(columns={
                "ActivityName": "Activity Name",
                "ActivityType": "Activity Type",
                "ProgramGroup": "Program Group",
                "Organization": "Landowner / Property",
                "DayOfWeek": "Day",
                "TotalVisitors": "Total Visitors",
                "VisitorsChildren": "Youth / Family Participants",
                "VolunteerHours": "Volunteer Hours",
            })

            st.dataframe(similar_table.head(25), use_container_width=True, hide_index=True)

            st.subheader("Planning Summary")

            best_month = month_perf.sort_values("AvgVisitors", ascending=False).head(1)
            best_day = day_perf.sort_values("AvgVisitors", ascending=False).head(1)
            best_property = property_perf.sort_values("AvgVisitors", ascending=False).head(1)

            summary_parts = []

            if not best_month.empty:
                summary_parts.append(f"Best month based on similar activities: **{best_month.iloc[0]['Month']}**")

            if not best_day.empty:
                summary_parts.append(f"Best day based on similar activities: **{best_day.iloc[0]['DayOfWeek']}**")

            if not best_property.empty:
                summary_parts.append(f"Best landowner/property based on similar activities: **{best_property.iloc[0]['Organization']}**")

            summary_parts.append(f"Expected average attendance: **{scenario_avg:.1f} visitors**")
            summary_parts.append(f"Expected average volunteer need: **{comparable['Volunteers'].mean():.1f} volunteers**")
            summary_parts.append(f"Expected youth/family participation: **{comparable['VisitorsChildren'].mean():.1f} participants**")

            st.markdown("\n\n".join([f"- {item}" for item in summary_parts]))

            st.info(
                "This section can later become a short planning summary for Kelley when reviewing a proposed activity."
            )
