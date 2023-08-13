"""Functions for preprocessing the U.S. Department of Labor PERM data.

This module contains functions that can be used to convert raw Excel files provided by the
U.S. Department of Labor into a single pandas.DataFrame object.

When this module is run as is with `python -m immimaps.preprocessing`, the full preprocessing
pipeline is applied to the files in the default data folder.
"""

import os
import re

import pandas as pd

from . import geography


# Certification status column name and its canonicalized aliases in the raw data
_STATUS_COLUMN = {'case_status': ['case_status']}

# Canonicalized certification statuses for data rows that are kept
_CERT_STATUSES = ('certified', 'certified-expired')

# Output column names and their canonicalized aliases in the raw data
_DATA_COLUMNS = {
    'case_number': ['case_number', 'case_no'],
    'fiscal_year': [], # obtained from the filename
    'employer_city': ['employer_city'],
    'employer_state': ['employer_state', 'employer_state_province'],
    'employer_postal_code': ['employer_postal_code'],
    'employer_country': ['employer_country'],
    'employer_num_employees': ['employer_num_employees'],
    'employer_year_established': ['employer_yr_estab', 'employer_year_commenced_business', 'emp_year_commenced_business'],
    'employer_economic_sector': ['us_economic_sector'],
    'job_title': ['job_info_job_title', 'job_title'],
    'job_city': ['job_info_work_city', 'worksite_city'],
    'job_state': ['job_info_work_state', 'worksite_state'],
    'job_postal_code': ['job_info_work_postal_code', 'worksite_postal_code'],
    'job_education_level': ['job_info_education', 'minimum_education'],
    'job_education_major': ['job_info_major', 'major_field_of_study'],
    'job_experience_months': ['job_info_experience_num_months', 'required_experience_months'],
    'job_wage_offer_from': ['wage_offer_from_9089', 'wage_offered_from_9089', 'wage_offered_from', 'wage_offer_from'],
    'job_wage_offer_to': ['wage_offer_to_9089', 'wage_offered_to_9089', 'wage_offered_to', 'wage_offer_to'],
    'job_wage_offer_unit_of_pay': ['wage_offer_unit_of_pay_9089', 'wage_offered_unit_of_pay_9089', 'wage_offer_unit_of_pay'],
    'prevailing_wage': ['pw_amount_9089', 'pw_wage'],
    'prevailing_wage_unit_of_pay': ['pw_unit_of_pay_9089', 'pw_unit_of_pay'],
    'prevailing_wage_soc_code': ['pw_soc_code'],
    'prevailing_wage_soc_title': ['pw_soc_title'],
    'prevailing_wage_job_title': ['pw_job_title_9089', 'pw_job_title'],
    'prevailing_wage_skill_level': ['pw_level_9089', 'pw_skill_level'],
    'worker_class_of_admission': ['class_of_admission'],
    'worker_country_of_citizenship': ['country_of_citzenship', 'country_of_citizenship'], # sic
    'worker_country_of_birth': ['fw_info_birth_country', 'foreign_worker_birth_country'],
    'worker_education_level': ['foreign_worker_info_education', 'foreign_worker_education'],
    'worker_education_major': ['foreign_worker_info_major'],
    'worker_education_year': ['fw_info_yr_rel_edu_completed', 'foreign_worker_yrs_ed_comp'],
    'worker_education_institution': ['foreign_worker_info_inst', 'foreign_worker_inst_of_ed'],
    'worker_education_country': ['foreign_worker_ed_inst_country'],
}

# Non-standard aliases used by DoL for postal abbreviations
_US_STATE_EXCEPTIONS = {'VI': ['Virgin Islands']}


### File input ###

def fiscal_year_from_filename(filename):
    """Determine fiscal year from a filename"""
    match = re.search(r'FY(\d+)', filename)
    if match is None:
        return None
    fiscal_year = int(match[1])
    if fiscal_year < 2000: # For example, 14 means 2014
        fiscal_year += 2000
    return fiscal_year

def read_xlsx(filename, cachedir=None):
    """Read XLSX file contents and optionally use pickled cache."""
    if cachedir is not None:
        basename = os.path.basename(filename)
        cachefile = os.path.join(cachedir, os.path.splitext(basename)[0] + '.bz2')
        if os.path.isfile(cachefile):
            data = pd.read_pickle(cachefile)
            return data
    data = pd.read_excel(filename) # slow
    if cachedir is not None:
        data.to_pickle(cachefile)
    return data


### DataFrame subset extraction and label canonicalization ###

def canonical_columns(data, cols_with_aliases):
    """Rename and select columns using name canonicalization and de-aliasing"""
    data = data.rename(columns=lambda col: col.lower().replace(' ', '_'))
    data = data.rename(columns={alias: k for k, v in cols_with_aliases.items() for alias in v})
    data = data[[col for col in data.columns if col in cols_with_aliases]]
    return data

def select_subset(data, fiscal_year):
    """Select certified rows and relevant columns"""
    status = canonical_columns(data, _STATUS_COLUMN).squeeze().str.lower().str.replace(' ', '_')
    data = canonical_columns(data, _DATA_COLUMNS)

    data = data[status.isin(_CERT_STATUSES)]
    data['fiscal_year'] = fiscal_year

    rowstats = pd.DataFrame(status.value_counts(dropna=False)).transpose()
    rowstats.index = [fiscal_year]

    colstats = pd.DataFrame(data.count()/data.shape[0]).transpose()
    colstats.index = [fiscal_year]

    return data, rowstats, colstats

def remove_duplicates(data):
    """For duplicates, keep only the most recent entry (assume data is sorted by fiscal year)"""
    data = data.drop_duplicates('case_number', keep='last')
    # TODO: collect info about duplicate removal
    return data


### Value canonicalization ###

def canonicalize_us_states(data, cols):
    """Convert U.S. state entries to uppercase postal abbreviations"""
    states = geography.us_states()
    states = {long: short for short, long in states.items()}
    for short, longs in _US_STATE_EXCEPTIONS.items():
        for long in longs:
            states[long] = short

    bad = dict()
    for col in cols:
        orig = data[col].copy()
        data[col] = data[col].astype('string').str.strip(' 1234567890')
        for long, short in states.items():
            data[col] = data[col].str.replace('^'+long, short, case=False, regex=True)
        data[col] = data[col].str.split(n=1).str.get(0)

        not_canonicalized = ~data[col].isin(states.values())
        data.loc[not_canonicalized,col] = None
        bad[col] = orig[not_canonicalized].value_counts()

    return data, bad

def canonicalize_postal_codes(data, cols):
    """Convert postal codes to strings of length five"""
    bad = dict()
    for col in cols:
        orig = data[col].copy()
        data[col] = (data[col]
                     .astype('string')
                     .str.extract(r'(\d{1,5})', expand=False)
                     .str.zfill(5))
        not_canonicalized = data[col].isna() & ~orig.isna()
        bad[col] = orig[not_canonicalized].value_counts()
    return data, bad

def canonicalize_wages(data, cols):
    """Convert wages to floats"""
    bad = dict()
    for col in cols:
        orig = data[col].copy()
        text = data[col].apply(type) == str
        data.loc[text,col] = pd.to_numeric(
            data.loc[text,col].str.replace(',', ''), errors='coerce')

        not_canonicalized = data[col].isna() & ~orig.isna()
        bad[col] = orig[not_canonicalized].value_counts()

    return data, bad

def canonicalize_unit_of_pay(data, cols):
    """Convert unit of pay to short standard form"""
    units = {
        'YEAR': 'YR',
        'MONTH': 'MTH',
        'BI-WEEKLY': 'BI',
        'WEEK': 'WK',
        'HOUR': 'HR'}
    bad = dict()
    for col in cols:
        orig = data[col].copy()
        data[col] = data[col].str.upper()
        for long, short in units.items():
            data[col] = data[col].str.replace('^'+long, short, case=False, regex=True)

        not_canonicalized = ~data[col].isin(units.values())
        data.loc[not_canonicalized,col] = None
        bad[col] = orig[not_canonicalized].value_counts()

    return data, bad

def canonicalize_values(data):
    """Try to canonicalize all values and their datatypes"""
    bad = dict()

    state_cols = [
        'employer_state',
        'job_state',
    ]
    data, bad_ = canonicalize_us_states(data, state_cols)
    bad |= bad_

    postal_cols = [
        'employer_postal_code',
        'job_postal_code',
    ]
    data, bad_ = canonicalize_postal_codes(data, postal_cols)
    bad |= bad_

    wage_cols = [
        'job_wage_offer_from',
        'job_wage_offer_to',
        'prevailing_wage',
    ]
    data, bad_ = canonicalize_wages(data, wage_cols)
    bad |= bad_

    unit_of_pay_cols = [
        'job_wage_offer_unit_of_pay',
        'prevailing_wage_unit_of_pay',
    ]
    data, bad_ = canonicalize_unit_of_pay(data, unit_of_pay_cols)
    bad |= bad_

    numeric_cols = [
        'fiscal_year',
        'employer_num_employees',
        'employer_year_established',
        'job_experience_months',
        'job_wage_offer_from',
        'job_wage_offer_to',
        'prevailing_wage',
        'worker_education_year',
    ]
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    for col in data.columns.difference(numeric_cols):
        data[col] = data[col].astype('string').str.upper()

    return data, bad


### Main entrypoint ###

def preprocess_directory(input_dir, output_dir=None):
    """Preprocess all raw data files in a directory and produce several new files"""
    if output_dir is None:
        output_dir = input_dir
    print('Input directory:', input_dir)
    print('Output directory:', output_dir)

    input_files = [f for f in os.listdir(input_dir) if os.path.splitext(f)[1]=='.xlsx']

    # Application status counts for each fiscal year
    status_counts = [pd.DataFrame(columns=_CERT_STATUSES, dtype='int')]
    # Percentages of data that is available for each column for each year
    avail_ratios = [pd.DataFrame(columns=list(_DATA_COLUMNS.keys()))]
    # Actual data, simplified and canonicalized
    perm = [pd.DataFrame(columns=list(_DATA_COLUMNS.keys()))]

    for ifile in input_files:
        fiscal_year = fiscal_year_from_filename(ifile)
        if fiscal_year is None:
            print('Skipping "{}" because the filename does not contain fiscal year.'.format(ifile))
            continue

        print('Reading "{}"...'.format(os.path.splitext(ifile)[0])) # reading xlsx or bz2
        data = read_xlsx(os.path.join(input_dir, ifile), output_dir)

        data, rowstats, colstats = select_subset(data, fiscal_year)

        perm.append(data)
        status_counts.append(rowstats)
        avail_ratios.append(colstats)

    print('Normalizing data and writing output files...')

    # Status counts will unavoidably include a small number of duplicates
    status_counts = pd.concat(status_counts).sort_index().rename_axis('FY')
    status_counts.to_pickle(os.path.join(output_dir, 'status_counts.pkl'))
    status_counts.to_csv(os.path.join(output_dir, 'status_counts.csv'))

    # Availability ratios before value canonicalization
    avail_ratios = pd.concat(avail_ratios).sort_index().rename_axis('FY')
    avail_ratios.to_pickle(os.path.join(output_dir, 'availability.pkl'))
    avail_ratios.to_csv(os.path.join(output_dir, 'availability.csv'))

    # Sort data, remove duplicates and canonicalize values
    perm = pd.concat(perm).sort_values(['case_number', 'fiscal_year'])
    perm = remove_duplicates(perm)
    perm = perm.set_index('case_number')
    perm, bad = canonicalize_values(perm)
    perm.to_pickle(os.path.join(output_dir, 'perm.pkl'))

    # Availability after value canonicalization; this does not distinguish
    # between missing columns and columns that have zero entries
    avail_ratios1 = perm.groupby('fiscal_year').apply(lambda x: x.count() / x.shape[0])
    avail_ratios1.to_pickle(os.path.join(output_dir, 'availability1.pkl'))
    avail_ratios1.to_csv(os.path.join(output_dir, 'availability1.csv'))


if __name__ == '__main__':
    selfdir = os.path.dirname(os.path.abspath(__file__))
    datadir = os.path.abspath(os.path.join(selfdir, '..', 'data', 'dol_perm'))
    preprocess_directory(datadir)
