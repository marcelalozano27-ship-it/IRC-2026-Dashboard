import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = "C:/Users/fongl/OneDrive/Documents/Capstone/IRC-2026/docs/eda_charts"
DATA = "C:/Users/fongl/OneDrive/Documents/Capstone/IRC-2026/data/LGO Participation 2025.csv"

df_raw = pd.read_csv(DATA, low_memory=False)
df = df_raw.drop_duplicates(subset='ActivityID').copy()
df['Date'] = pd.to_datetime(df['Date'])
df['Month'] = df['Date'].dt.to_period('M')
df['DayOfWeek'] = df['Date'].dt.day_name()

PALETTE = ['#2E7D6E', '#5BA08A', '#A8D5C2', '#F4A261', '#E76F51']
PLT_STYLE = {'figure.facecolor': 'white', 'axes.facecolor': '#F8F9FA',
             'axes.grid': True, 'grid.alpha': 0.4, 'axes.spines.top': False,
             'axes.spines.right': False}
plt.rcParams.update(PLT_STYLE)
plt.rcParams['font.family'] = 'sans-serif'

# ── CHART 1: Capacity Utilization Distribution ──────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
df['util'] = df['TotalVisitors'] / df['total_spaces'].replace(0, np.nan) * 100
util_clean = df['util'].dropna().clip(upper=150)

labels = ['<25%', '25–50%', '50–75%', '75–100%', '>100%']
bins = [0, 25, 50, 75, 100, 151]
counts, _ = np.histogram(util_clean, bins=bins)
bars = ax.bar(labels, counts, color=PALETTE, edgecolor='white', linewidth=1.2, width=0.6)

for bar, count in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
            f'{count}\n({count/len(util_clean)*100:.0f}%)',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.axvline(x=0.5, ymin=0, ymax=0, color='none')  # spacer
ax.set_title('Capacity Utilization Distribution\n1,862 Events · 2025', fontsize=13, fontweight='bold', pad=12)
ax.set_xlabel('Utilization Bucket', fontsize=11)
ax.set_ylabel('Number of Events', fontsize=11)
ax.set_ylim(0, max(counts) * 1.2)

# Annotation: median
median_util = util_clean.median()
ax.annotate(f'Median utilization: {median_util:.0f}%\n25% of events had 0 visitors',
            xy=(0.02, 0.92), xycoords='axes fraction',
            fontsize=10, color='#555',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#fff3cd', alpha=0.9))

plt.tight_layout()
plt.savefig(f'{OUT}/01_capacity_utilization.png', dpi=150, bbox_inches='tight')
plt.close()
print('Chart 1 saved.')

# Verification
print(f'  VERIFY - Events <25% full: {counts[0]} ({counts[0]/len(util_clean)*100:.1f}%)')
print(f'  VERIFY - Events with 0 visitors: {(df["TotalVisitors"]==0).sum()} ({(df["TotalVisitors"]==0).sum()/len(df)*100:.1f}%)')
print(f'  VERIFY - Median utilization: {median_util:.1f}%')


# ── CHART 2: No-Show Rate by Activity Type ──────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
active = df[df['ActivityStatus'] != 'Cancelled'].copy()
ns = active.groupby('ActivityType').agg(
    NoShows=('VisitorsNoShow', 'sum'),
    Registered=('VisitorsRegistered', 'sum')
).reset_index()
ns = ns[ns['Registered'] > 20].copy()
ns['NoShowRate'] = ns['NoShows'] / ns['Registered'] * 100
ns = ns.sort_values('NoShowRate', ascending=True)

colors = ['#E76F51' if r > 30 else '#F4A261' if r > 20 else '#5BA08A' for r in ns['NoShowRate']]
bars = ax.barh(ns['ActivityType'], ns['NoShowRate'], color=colors, edgecolor='white', height=0.6)

for bar, (_, row) in zip(bars, ns.iterrows()):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{row['NoShowRate']:.1f}%  ({int(row['NoShows'])}/{int(row['Registered'])})",
            va='center', fontsize=9.5)

ax.axvline(x=ns['NoShows'].sum()/ns['Registered'].sum()*100,
           color='#333', linestyle='--', linewidth=1.2, label=f"Overall avg: {ns['NoShows'].sum()/ns['Registered'].sum()*100:.1f}%")
ax.legend(fontsize=10)
ax.set_title('No-Show Rate by Activity Type\n(Active events only, ≥20 registered)', fontsize=13, fontweight='bold', pad=12)
ax.set_xlabel('No-Show Rate (%)', fontsize=11)
ax.set_xlim(0, 75)
plt.tight_layout()
plt.savefig(f'{OUT}/02_noshow_by_type.png', dpi=150, bbox_inches='tight')
plt.close()
print('Chart 2 saved.')
print(f'  VERIFY - Training no-show rate: {ns[ns["ActivityType"]=="Training"]["NoShowRate"].values}')
print(f'  VERIFY - Overall no-show rate: {ns["NoShows"].sum()/ns["Registered"].sum()*100:.1f}%')


# ── CHART 3: Monthly Events & Attendance ────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(10, 5))
active_monthly = df[df['ActivityStatus'] != 'Cancelled'].copy()
monthly_events = active_monthly.groupby('Month').size()
monthly_visitors = active_monthly.groupby('Month')['TotalVisitors'].sum()

months_str = [str(m) for m in monthly_events.index]
x = np.arange(len(months_str))

ax1.bar(x, monthly_events.values, color='#2E7D6E', alpha=0.75, label='Events', width=0.5)
ax1.set_ylabel('Number of Events', color='#2E7D6E', fontsize=11)
ax1.tick_params(axis='y', labelcolor='#2E7D6E')

ax2 = ax1.twinx()
ax2.plot(x, monthly_visitors.values, color='#E76F51', marker='o', linewidth=2.2,
         markersize=6, label='Total Visitors')
ax2.set_ylabel('Total Visitors', color='#E76F51', fontsize=11)
ax2.tick_params(axis='y', labelcolor='#E76F51')
ax2.set_facecolor('none')

ax1.set_xticks(x)
ax1.set_xticklabels([m[5:] for m in months_str], rotation=0)
ax1.set_title('Monthly Events and Attendance · 2025\n(Cancelled events excluded)', fontsize=13, fontweight='bold', pad=12)

lines1 = mpatches.Patch(color='#2E7D6E', alpha=0.75, label='Events (left axis)')
lines2 = plt.Line2D([0],[0], color='#E76F51', marker='o', linewidth=2, label='Visitors (right axis)')
ax1.legend(handles=[lines1, lines2], loc='upper right', fontsize=10)

plt.tight_layout()
plt.savefig(f'{OUT}/03_monthly_events_attendance.png', dpi=150, bbox_inches='tight')
plt.close()
print('Chart 3 saved.')
print(f'  VERIFY - Peak events month: {monthly_events.idxmax()} ({monthly_events.max()} events)')
print(f'  VERIFY - Peak visitors month: {monthly_visitors.idxmax()} ({monthly_visitors.max()} visitors)')


# ── CHART 4: Participant Retention ──────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(10, 5))

user_counts = df_raw.groupby('user_id').size()
once = (user_counts == 1).sum()
multi = (user_counts > 1).sum()

# Pie
axes[0].pie([once, multi],
            labels=[f'Attended once\n{once:,} ({once/len(user_counts)*100:.0f}%)',
                    f'Attended 2+ times\n{multi:,} ({multi/len(user_counts)*100:.0f}%)'],
            colors=['#5BA08A', '#2E7D6E'], startangle=90,
            wedgeprops=dict(edgecolor='white', linewidth=2),
            textprops={'fontsize': 11})
axes[0].set_title('Participant Retention\n5,840 unique users · 2025', fontsize=12, fontweight='bold')

# Frequency histogram
freq_bins = [1,2,3,4,5,6,10,20,50,200]
freq_labels = ['1','2','3','4','5','6–9','10–19','20–49','50+']
freq_counts = []
for i in range(len(freq_bins)-1):
    lo, hi = freq_bins[i], freq_bins[i+1]
    freq_counts.append(((user_counts >= lo) & (user_counts < hi)).sum())

colors_freq = ['#A8D5C2' if i==0 else '#5BA08A' if i<3 else '#2E7D6E' for i in range(len(freq_labels))]
axes[1].bar(freq_labels, freq_counts, color=colors_freq, edgecolor='white', linewidth=1)
for i, (label, count) in enumerate(zip(freq_labels, freq_counts)):
    if count > 0:
        axes[1].text(i, count + 10, str(count), ha='center', fontsize=9, fontweight='bold')
axes[1].set_title('Booking Frequency Distribution', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Number of Bookings', fontsize=10)
axes[1].set_ylabel('Number of Users', fontsize=10)

plt.tight_layout()
plt.savefig(f'{OUT}/04_participant_retention.png', dpi=150, bbox_inches='tight')
plt.close()
print('Chart 4 saved.')
print(f'  VERIFY - Attended once: {once} ({once/len(user_counts)*100:.1f}%)')
print(f'  VERIFY - Attended 2+ times: {multi} ({multi/len(user_counts)*100:.1f}%)')
print(f'  VERIFY - Max bookings: {user_counts.max()}')


# ── CHART 5: Cancellation Rate by Activity Type ─────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
cancel_stats = df.groupby('ActivityType').agg(
    Total=('ActivityStatus', 'count'),
    Cancelled=('ActivityStatus', lambda x: (x=='Cancelled').sum())
).reset_index()
cancel_stats = cancel_stats[cancel_stats['Total'] >= 5].copy()
cancel_stats['CancelRate'] = cancel_stats['Cancelled'] / cancel_stats['Total'] * 100
cancel_stats = cancel_stats.sort_values('CancelRate', ascending=True)

colors = ['#E76F51' if r > 20 else '#F4A261' if r > 14 else '#5BA08A' for r in cancel_stats['CancelRate']]
bars = ax.barh(cancel_stats['ActivityType'], cancel_stats['CancelRate'],
               color=colors, edgecolor='white', height=0.6)
for bar, (_, row) in zip(bars, cancel_stats.iterrows()):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f"{row['CancelRate']:.1f}%  ({int(row['Cancelled'])}/{int(row['Total'])})",
            va='center', fontsize=9.5)

overall_cancel = len(df[df['ActivityStatus']=='Cancelled']) / len(df) * 100
ax.axvline(x=overall_cancel, color='#333', linestyle='--', linewidth=1.2,
           label=f'Overall: {overall_cancel:.1f}%')
ax.legend(fontsize=10)
ax.set_title('Cancellation Rate by Activity Type · 2025', fontsize=13, fontweight='bold', pad=12)
ax.set_xlabel('Cancellation Rate (%)', fontsize=11)
ax.set_xlim(0, 35)
plt.tight_layout()
plt.savefig(f'{OUT}/05_cancellation_by_type.png', dpi=150, bbox_inches='tight')
plt.close()
print('Chart 5 saved.')
print(f'  VERIFY - Overall cancellation rate: {overall_cancel:.1f}%')
print(f'  VERIFY - Equestrian: {cancel_stats[cancel_stats["ActivityType"]=="Equestrian"][["CancelRate","Cancelled","Total"]].values}')


# ── CHART 6: Top Participant Cities ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
city_norm = df_raw['city'].str.strip().str.title()
city_counts = city_norm.value_counts().head(12)

colors_city = ['#2E7D6E' if c == 'Irvine' else '#5BA08A' for c in city_counts.index]
bars = ax.barh(city_counts.index[::-1], city_counts.values[::-1],
               color=colors_city[::-1], edgecolor='white', height=0.65)
for bar, count in zip(bars, city_counts.values[::-1]):
    ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
            f'{count:,} ({count/len(df_raw)*100:.1f}%)', va='center', fontsize=9.5)

ax.set_title('Participant Bookings by City · 2025\n(City field normalized)', fontsize=13, fontweight='bold', pad=12)
ax.set_xlabel('Number of Bookings', fontsize=11)
ax.set_xlim(0, city_counts.max() * 1.25)
irvine_patch = mpatches.Patch(color='#2E7D6E', label='Irvine (host city)')
other_patch = mpatches.Patch(color='#5BA08A', label='Other OC cities')
ax.legend(handles=[irvine_patch, other_patch], fontsize=10)
plt.tight_layout()
plt.savefig(f'{OUT}/06_participant_cities.png', dpi=150, bbox_inches='tight')
plt.close()
print('Chart 6 saved.')
irvine_total = (city_norm == 'Irvine').sum()
print(f'  VERIFY - Irvine bookings (normalized): {irvine_total} ({irvine_total/len(df_raw)*100:.1f}%)')


print('\nAll charts saved to:', OUT)
