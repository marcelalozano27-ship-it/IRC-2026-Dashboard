# IRC 2026 MSBA Capstone — Project Summary

**Client:** Irvine Ranch Conservancy (IRC) — manages ~30,000 acres of open space in collaboration with OC Parks, the City of Irvine, and the City of Newport Beach.

**Project title:** Program Engagement Analytics and Capacity Optimization for Community Outreach

## The problem

IRC runs public "Let's Go Outside" outreach programs led by volunteers and staff. These programs vary widely in timing, content, attendance, and staffing, and IRC has no structured way to see what's working, where the gaps are, or how to allocate resources. The project builds an analytic framework that turns their program data into decisions about scheduling, capacity planning, and program mix.

## What we're building (deliverables)

- A clean, standardized dataset built from Let's Go Outside activity exports
- Exploratory analysis of engagement trends
- Quantified geographic and activity-based engagement gaps
- Predictive models for attendance, capacity utilization, and/or no-show dynamics
- An interactive dashboard staff can refresh themselves (Power BI preferred)

## Data

Activity exports from LetsGoOutside.org, shared via SharePoint in Excel/CSV format. Variables include date, time, activity name/type/subtype, location, host org, registered participants, no-shows, walk-ups, children, total guests, staff count, staff hours, total spaces, and private/unlisted flags. IRC confirms access by **March 17**.

## Key constraints

- Data stays on internal storage unless IRC explicitly approves cloud (AWS/Azure/Google Cloud). Confirm this early, since it shapes the whole toolchain
- No identifiable information shared publicly without IRC authorization
- Microsoft 365 ecosystem; Python/R/SQL are fine for analysis; **Power BI Desktop** is preferred for the dashboard (free, sustainable for staff to maintain after handoff)
- Methods: descriptive and predictive analytics, validated against reasonable baselines. No required project management methodology.

## Stakeholders and end users

IRC Community Engagement & Education staff are the primary users. Secondary beneficiaries are OC Parks, the City of Irvine, and the City of Newport Beach (the landowners IRC manages for).

## Contacts

- **Chris Eljenholm** — Program Coordinator, project liaison (celjenholm@irconservancy.org)
- **David Raetz** — VP & Chief Administration Officer, legal/NDA liaison (draetz@irconservancy.org)
- **Yi-Chin Fang** — yfang@irconservancy.org
- **Kelley Brugmann** — kbrugmann@irconservancy.org

## Caveat on dates

The dates in the source document come from a 2025 template (it also leaves a stray "CHLA" reference in the deliverables boilerplate). Treat the timeline as a pattern, not literal, and confirm the actual 2026 dates with faculty.
