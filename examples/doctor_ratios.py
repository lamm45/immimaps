#!/usr/bin/env python3
"""Show percentages of doctoral degree holders among new immigrants

This is an example script that reads the preprocessed PERM data
(created by `immimaps.preprocessing` module) and displays on the
U.S. map the percentages of doctoral degree holders among
certified PERM applicants by job state.

"""

import os.path as osp
import sys

import matplotlib.offsetbox
import matplotlib.pyplot as plt
import pandas as pd

rootdir = osp.abspath(osp.join(osp.dirname(__file__), '..'))
sys.path.append(rootdir)
import immimaps.cartography


# Read data
datafile = osp.join(rootdir, 'data', 'dol_perm', 'perm.pkl')
data = pd.read_pickle(datafile)

# Compute percentages of immigrants with doctoral degree
doctorate_ratio = data.groupby('job_state')['worker_education_level'].\
    apply(lambda x: 100 * (x=='DOCTORATE').sum() / x.count())

# Check available years
years = data.loc[data['worker_education_level'].notna(),'fiscal_year'].unique()

# Draw data on map
fig = plt.figure(figsize=(12, 7))
ax, sm = immimaps.cartography.draw_us_map(doctorate_ratio.to_dict(),
                                          fig=fig, cmap='BuPu')
plt.colorbar(sm, ax=ax)
plt.tight_layout()

# Add texts
titletxt = (
    'Percentage of doctoral degree holders among certified PERM applicants '
    'by job state, fiscal years {}-{}'
).format(min(years), max(years))
plt.title(titletxt)
infotxt = matplotlib.offsetbox.AnchoredText(
    'Data: U.S. Department of Labor.\n'
    'Made with Natural Earth.', loc=4)
ax.add_artist(infotxt)

# Save (optional) and display
# plt.savefig('doctor_ratios.png')
plt.show()
