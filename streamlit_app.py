# To ignore unimporant system warnings
import warnings
warnings.filterwarnings("ignore")

# We will use Pandas, Numpy, and Matplotlib which is a package for visualization with Python
import pandas as pd
#pd.set_option('display.max_rows',1000)
import numpy as np
import geopandas as gpd
from datetime import datetime
from geodatasets import get_path

# This is a library for accessing and parsing data through URLs
import urllib.request, json 
import urllib.parse
from urllib.parse import urlencode

# Using folium to create a map
import folium
from folium import plugins
import matplotlib.pyplot as plt
import seaborn as sns # visualization styling package
import branca  # For color gradient
%matplotlib inline 

def fetch_bus_data(route_id= None, date_start = None, date_end = None,borough = None, limit=1000):
    # Define API endpoint and base query
    BASE_API = "https://data.ny.gov/resource/58t6-89vi.json?"
    query_speeds = {
        '$select': 'route_id, direction, AVG(average_road_speed) as avg_speed',
        '$group': 'route_id, direction',
        '$limit': limit,
        '$order': 'avg_speed'  # Order by timestamp,
    }
    # Fetch data
    url_speeds = BASE_API + urlencode(query_speeds)
    response_speeds = urllib.request.urlopen(url_speeds)
    data_speeds = json.loads(response_speeds.read().decode())
    
    # Only add WHERE clause if route_id is specified
    if route_id:
        query_speeds['$where'] = f'route_id="{route_id}"'
    if borough:
        query_speeds['$where'] = f'borough="{borough}"'
    if date_start:
        query_speeds['$where'] = f'timestamp=">={date_start}T00:00:00"'
    if date_end:
        query_speeds['$where'] = f'timestamp=">={date_end}T00:00:00"'
    # Convert to DataFrame
    df_speeds = pd.DataFrame(data_speeds)
    return df_speeds

# Example usage
df = fetch_bus_data(limit=100)
df
