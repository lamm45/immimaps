# immimaps: United States immigration statistics on map

This repository contains a Python package that can be used to visualize United States immigration statistics on U.S. (and later, world) maps.
Currently, only PERM data is supported.
PERM data refers to employer-sponsored applications for lawful permanent resident, also known as employment-based green card applications.


## Downloading the data
The PERM data is publicly available at the U.S. Department of Labor website at:
https://www.dol.gov/agencies/eta/foreign-labor/performance

The downloadable Microsoft Excel (.xlsx) files can be found under "Disclosure Data" section and under "PERM Program".
Each fiscal year has its own file, and the total amount of data from fiscal years between 2008 and 2022 is about 620 megabytes.
If you prefer, you can choose to download a subset of the available data.

If you are using bash and wget, you can also automatically download all supported files by running the script `download.bash` which is found in the folder `data/dol_perm` in this repository.
The downloaded files will be placed in that same folder.


## Getting started with the code
This package depends on [cartopy](https://scitools.org.uk/cartopy/), [pandas](https://pandas.pydata.org/) and [openpyxl](https://openpyxl.readthedocs.io/en/stable/) packages.
For example, if you are using conda, the Python environment can be created and activated as follows:
```
conda create --name immimaps cartopy pandas openpyxl
conda activate immimaps
```

If the downloaded data files are stored in the default location `data/dol_perm`, data preprocessing can be performed by running
```
python3 -m immimaps.preprocessing
```
from the repository root folder.
This will create a pickle file `data/dol_perm/perm.pkl` which will contain the most relevant PERM application information from all available fiscal years in a single `pandas.DataFrame` object.
Applications that are denied or withdrawn are excluded from this file.
The preprocessing step will also output several intermediate files that may or may not be of interest.

## Example
As an example, we can show the percentages of new immigrants that hold a doctoral degree in different U.S. states.
A simplified Python code would look like this:
```python
import pandas as pd
import immimaps.cartography

datafile = '/path/to/perm.pkl'
data = pd.read_pickle(datafile)

doctorate_ratio = data.groupby('job_state')['worker_education_level'].\
    apply(lambda x: 100 * (x=='DOCTORATE').sum() / x.count())

ax, sm = immimaps.cartography.draw_us_map(doctorate_ratio.to_dict())
# add title etc...

plt.show()
```

The output would look similar to this:
[![Doctoral degree percentages by state](/doc/doctor_ratios.png)](/doc/doctor_ratios.png)

A full example script is available in the `examples` subfolder.
