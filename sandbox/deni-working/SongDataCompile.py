# -*- coding: utf-8 -*-
"""
Created on Mon Oct 12 08:08:32 2026

@author: deni_
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns
import re
import glob
import os
import plotly.express as px
import plotly.offline as pyo
import plotly.graph_objects as go

def convert_coordinates(coord):
    if pd.isna(coord):
        return float('nan')
    coord = str(coord).strip().upper()
    match = re.search(r'-?\d+(?:\.\d+)?', coord)
    if not match:
        return float('nan')
    value = float(match.group())
    if 'S' in coord or 'W' in coord:
        value = -abs(value)
    elif 'N' in coord or 'E' in coord:
        value = abs(value)
    return value

import pandas as pd
import numpy as np
import re

def standardize_sampling_year(value):
    """
    Returns:
        years: list of individual years, or [np.nan] if not interpretable
        review: whether the entry needs manual review
    """
    if pd.isna(value) or str(value).strip() == '':
        return [np.nan], True
    s = str(value).strip()
    # Single year: YYYY
    if re.fullmatch(r'\d{4}', s):
        return [int(s)], False
    # Year range: YYYY-YYYY or YYYY-YYYY(mean)
    match = re.fullmatch(
        r'(\d{4})\s*-\s*(\d{4})(?:\s*\(mean\))?',
        s, flags=re.IGNORECASE)
    if match:
        start, end = map(int, match.groups())
        if start <= end:
            return list(range(start, end + 1)), False
        else:
            return [np.nan], True
    # Formats: YYYY.MM, YYYY-dry, YYYY-wet, wet-YYYY, dry-YYYY
    match = re.fullmatch(
        r'(?:(\d{4})(?:\.\d+|[-\s](?:wet|dry))|'
        r'(?:wet|dry)[-\s](\d{4}))',
        s, flags=re.IGNORECASE)
    if match:
        year = next(
            int(g) for g in match.groups() if g is not None)
        return [year], False
    # Format: Year X
    match = re.fullmatch(
        r'Year\s+(\d+)',
        s, flags=re.IGNORECASE)
    if match:
        return [np.nan], True
    # Formats: Xst Year, Xnd Year, Xrd Year, Xth Year
    match = re.fullmatch(
        r'\d+(?:st|nd|rd|th)\s+Year',
        s, flags=re.IGNORECASE)
    if match:
        return [np.nan], True
    # Text entries such as "Wetter year" or "Normal year"and any other unrecognized formats
    return [np.nan], True

#%% Read in csv's

# Folder containing CSV files
folder = r"C:\Users\deni_\OneDrive - USNH\Desktop\post doc\SSECR - course _ project\Songetal2019_updateddata\Updated version_A global database of plant productivity and ecosystem carbon exchange from GCMEs"

# Get all CSV files in the folder
csv_files = glob.glob(os.path.join(folder, "*.csv"))

# Read, clean, and concatenate
dfs = []

for file in csv_files:
    df = pd.read_csv(file, encoding='latin1', skiprows=1)
    df = df.drop(columns=['C_M', 'C_SE', 'C_SD', 'C_N', 'T_M', 'T_SE', 'T_SD', 'T_N'],errors='ignore')
    df['source_file'] = os.path.basename(file)
    dfs.append(df)
    
song_data = pd.concat(dfs, ignore_index=True)

#Fix lat lon
song_data['Latitude'] = song_data['Latitude(Degrees)'].apply(convert_coordinates)
song_data['Longitude'] = song_data['Longitude(Degrees)'].apply(convert_coordinates)

song_data = song_data[['Citations', 'References', 'Vol_FP', 'Country', 'Site',
       'Site (S) number', 'Latitude', 'Longitude','Elevation(m)', 'MAT(¡ãC)', 'MAP(mm)', 'Wetness', 'Ecosystem',
       'Community', 'Other conditions', 'SamplingY', 'Exp Type', 'Exp GCDFs', 'Treatment',
       'WarmingF', 'AT+(¡æ)', 'ST+(¡æ)', 'IP+(mm)', 'DP-(mm)', 'eCO2F',
       'eCO2+(ppm)', 'eN dose(g N/m2/year)', 'Variable', 'Unit', 
       'source_file']]

#Clean columns
song_data = song_data.rename(columns = {'Site (S) number': 'Site_number',
                                       'Elevation(m)' : 'Elevation_m',
                                       'MAT(¡ãC)': 'MAT_degC',
                                       'MAP(mm)': 'MAP_mm',
                                       'Wetness': 'Wetness_Index',
                                       'Other conditions': 'Other_conditions',
                                       'Exp Type': 'Exp_Type',
                                       'Exp GCDFs' : 'Exp_GCDFs',
                                       'AT+(¡æ)': 'AirTempIncrease_degC',
                                       'ST+(¡æ)': 'SoilTempIncrease_degC',
                                       'IP+(mm)' : 'PrcpIncrease_mm',
                                       'DP-(mm)': 'PrcpDecrease_mm',
                                       'eCO2+(ppm)' : 'eCO2Increase_ppm',
                                       'eN dose(g N/m2/year)': 'NAdditionDose_gNm2yr'})
#write csv
song_data.to_csv(r'C:\Users\deni_\OneDrive - USNH\Desktop\post doc\SSECR - course _ project\Songetal2019_updateddata\Song_Data_Compiled_101226_DM.csv')

#%% Format year column
song_data_site = song_data[['Citations', 'References', 'Latitude', 'Longitude', 'SamplingY', 'Exp_Type', 'Exp_GCDFs']].drop_duplicates()

# Preserve the original SamplingY column
song_data_site['SamplingY_original'] = song_data_site['SamplingY']

# Parse each row
parsed = song_data_site['SamplingY_original'].apply(standardize_sampling_year)

song_data_site['SamplingY_standardized'] = parsed.apply(lambda x: x[0])
song_data_site['SamplingY_review'] = parsed.apply(lambda x: x[1])

# Expand year ranges into separate rows, repeating all other information
song_data_site = song_data_site.explode('SamplingY_standardized', ignore_index=True)

# Keep the standardized year as a nullable integer
song_data_site['SamplingY_standardized'] = song_data_site['SamplingY_standardized'].astype('float64')

#subset study's to review
song_data_flag = song_data_site.loc[song_data_site['SamplingY_review'] == True,]
song_data_flag.to_csv(r'C:\Users\deni_\OneDrive - USNH\Desktop\post doc\SSECR - course _ project\Song_sites_with_no_years.csv')

#subset study's with known duration
song_data_site_clean = song_data_site.loc[song_data_site['SamplingY_review'] == False,]

#%% Determine study duration

# Define what identifies a unique experiment
experiment_cols = [ 'Citations', 'References', 'Latitude','Longitude','Exp_Type','Exp_GCDFs']


# Group by unique experiment and calculate duration
song_data_duration = (song_data_site_clean.groupby(experiment_cols, dropna=False).agg(
        Start_Year=('SamplingY_standardized', 'min'),
        End_Year=('SamplingY_standardized', 'max'),
        N_Years=('SamplingY_standardized', 'nunique')).reset_index())

# Calculate study duration in years, inclusive of both endpoints
song_data_duration['Study_Duration'] = (song_data_duration['End_Year']- song_data_duration['Start_Year'] + 1)

# Convert years to nullable integers
song_data_duration[['Start_Year', 'End_Year','N_Years', 'Study_Duration']] = (
    song_data_duration[['Start_Year', 'End_Year','N_Years', 'Study_Duration']]
    .astype('float64'))

#plot histogram of study duration
plt.hist(song_data_duration.Study_Duration, bins = 21)
plt.xlabel('Study Duration (years)')
plt.ylabel('Number of Studies in Song et al 2019')

#subset sites with > 5 years of data (assuming this is accurate)
song_data_dur5yrs = song_data_duration.loc[song_data_duration.Study_Duration >4, ] #80 sites with 5 years of data or more
song_data_dur5yrs.to_csv(r'C:\Users\deni_\OneDrive - USNH\Desktop\post doc\SSECR - course _ project\Song_data_StudyDur5yrs.csv')

#%% Map of sites 

fig = px.scatter_geo(
    song_data_site,
    lat='Latitude',
    lon='Longitude',
    hover_name = 'Citations',
    #color = 'Study_Duration'
    #color = 'Exp_GCDFs'
)

# Customize marker appearance
#fig.update_traces(marker=dict(size=7,  opacity=0.3))

# Configure global map
fig.update_layout(
    title='Global Distribution of Sampling Locations',
    geo=dict(
        scope='world',
        showland=True,
        landcolor='lightgray',
        showcountries=True,
        countrycolor='white',
        showcoastlines=True,
        coastlinecolor='gray',
        showocean=True,
        oceancolor='lightblue',
        showlakes=True,
        lakecolor='lightblue',
        projection_type='natural earth',
        bgcolor='white'
    )
)

# Save interactive HTML
fig.write_html(
    r"C:\Users\deni_\OneDrive - USNH\Desktop\post doc\SSECR - course _ project\Song_sampling_locations.html",
    include_plotlyjs=True,
    full_html=True,
    auto_open=True
)

