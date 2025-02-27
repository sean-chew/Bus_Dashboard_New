import streamlit as st
import pandas as pd
import urllib.request
import json
import zipfile
import requests
from urllib.parse import urlencode
import warnings
import geopandas as gpd
import io
import shapely as sp
import streamlit.components.v1 as components
from datetime import datetime

warnings.filterwarnings("ignore")
# Add route click interactivity
route_click_js = """
<script>
function highlightRoute(routeId) {
    // Get all polylines on the map
    var allRoutes = document.querySelectorAll('.leaflet-interactive');
    
    allRoutes.forEach(route => {
        if (route.id === routeId) {
            // Highlight the selected route
            route.style.strokeWidth = "6";  // Make the selected route thicker
            route.style.strokeOpacity = "1";  // Full opacity
        } else {
            // Dim all other routes
            route.style.strokeOpacity = "0.2";  // Lower opacity for others
        }
    });
}
</script>
"""

# URL to the GTFS data
url_b = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_b.zip"
url_bx = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_bx.zip"
url_m = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_m.zip"
url_q = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_q.zip"
url_si = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_si.zip"
url_busco = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_busco.zip"

# Function to download and extract the ZIP file from the URL
@st.cache_data(show_spinner=False)
def fetch_and_extract_gtfs(url):
    # Download the file from the URL
    response = requests.get(url)
    
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Create a BytesIO object from the response content
        zip_file = io.BytesIO(response.content)
        
        # Extract the ZIP file in memory
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # Read 'shapes.txt' into DataFrame
            with zip_ref.open('shapes.txt') as f_shapes:
                df_shapes = pd.read_csv(f_shapes)
            
            # Read 'trips.txt' into DataFrame
            with zip_ref.open('trips.txt') as f_trips:
                df_trips = pd.read_csv(f_trips)
            
            # Return the DataFrames
            return df_shapes, df_trips
    else:
        raise Exception(f"Failed to download file, status code: {response.status_code}")

# Fetch and display stops data
@st.cache_data(show_spinner=False)
def make_gdf(df_shapes, df_trips):
    df_shapes['shape_pt_sequence'] = pd.to_numeric(df_shapes['shape_pt_sequence'])
    # Sort data to ensure points are in correct order
    df_shapes = df_shapes.sort_values(by=['shape_id', 'shape_pt_sequence'])
    # Group by shape_id and create LineString geometry
    lines = df_shapes.groupby('shape_id').apply(
        lambda x: sp.geometry.LineString(x[['shape_pt_lon', 'shape_pt_lat']].values)
    ).reset_index(name='geometry')
    # # Convert to GeoDataFrame
    df_trips = df_trips[['route_id','trip_headsign','shape_id']]
    df_trips = df_trips.drop_duplicates().reset_index(drop = True)
    gdf = gpd.GeoDataFrame(lines, geometry='geometry', crs="EPSG:4326")  # WGS 84 CRS
    gdf_join = gdf.merge(df_trips, on='shape_id', how='left')\
    .groupby(by = ["route_id","trip_headsign"])\
    .first()\
    .reset_index()\
    .drop('shape_id',axis = 1)
    return gdf_join

@st.cache_data(show_spinner=False)
def load_all_gtfs():
    urls = {
        "Brooklyn": url_b,
        "Bronx": url_bx,
        "Manhattan": url_m,
        "Queens": url_q,
        "Staten Island": url_si,
        "busco": url_busco

    }
    gdfs = {}
    for borough, url in urls.items():
        df_shapes, df_trips = fetch_and_extract_gtfs(url)
        gdfs[borough] = make_gdf(df_shapes, df_trips)
    
    return gdfs

# Function to fetch bus data
@st.cache_data(show_spinner=False)
def fetch_bus_data(route_id=None, date_start=None, date_end=None, time_start=None, time_end=None, borough=None, limit=1000):
    # Define API endpoint and base query
    BASE_API = "https://data.ny.gov/resource/58t6-89vi.json?"
    query_speeds = {
        '$select': 'route_id, AVG(average_road_speed) as avg_speed',
        '$group': 'route_id',
        '$limit': limit,
        '$order': 'avg_speed'
    }
    
    # Build WHERE clause based on filters
    where_conditions = []
    
    if route_id:
        where_conditions.append(f'route_id="{route_id}"')
    if borough:
        where_conditions.append(f'borough="{borough}"')
    if date_start:
        where_conditions.append(f'timestamp>="{date_start}T{time_start if time_start else "00:00:00"}"')
    if date_end:
        where_conditions.append(f'timestamp<="{date_end}T{time_end if time_end else "23:59:59"}"')
    
    if where_conditions:
        query_speeds['$where'] = ' AND '.join(where_conditions)
    
    # Fetch data
    url_speeds = BASE_API + urlencode(query_speeds)
    response_speeds = urllib.request.urlopen(url_speeds)
    data_speeds = json.loads(response_speeds.read().decode())
    
    # Convert to DataFrame
    df_speeds = pd.DataFrame(data_speeds)
    return df_speeds

@st.cache_data(show_spinner=False)
def get_latest_data_date():
    # Socrata Open Data API endpoint for the dataset
    dataset_id = "58t6-89vi"
    base_url = f"https://data.ny.gov/resource/{dataset_id}.json"

    # Query parameters to get the most recent date
    query = {
        "$select": "MAX(timestamp) as latest_date"
    }

    # Make the request to the API
    response = requests.get(base_url, params=query)

    if response.status_code == 200:
        data = response.json()
        if data and 'latest_date' in data[0]:
            # Convert the date string to a datetime object
            latest_date = datetime.strptime(data[0]['latest_date'], '%Y-%m-%dT%H:%M:%S.%f')
            return latest_date
        else:
            raise ValueError("No date information found in the dataset.")
    else:
        raise ConnectionError(f"Failed to fetch data: {response.status_code}")

# @st.cache_data(show_spinner=False)
def render_mapbox_map(gdf_routes):
    mapbox_access_token = st.secrets["mapbox_access_token"]

    # Convert route geometries to JSON format
    route_features = []
    for _, row in gdf_routes.iterrows():
        feature = {
            "type": "Feature",
            "properties": {
                "route_id": row["route_id"],
                "avg_speed": row["avg_speed"],
                "trip_headsign": row["trip_headsign"]
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lon, lat in row.geometry.coords]
            }
        }
        route_features.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "features": route_features
    }


    # Read the HTML template hello
    with open("mapbox_template.html", "r") as file:
        html_template = file.read()

    # Replace placeholders with actual data
    html_code = html_template.replace("{mapbox_access_token}", mapbox_access_token)
    html_code = html_code.replace("{geojson_data}", json.dumps(geojson_data))

    return html_code

# Set up the Streamlit page
st.title("NYC Bus Data Explorer")
# Sidebar controls
st.sidebar.header("Filters")
# Date range selector
col1, col2 = st.sidebar.columns(2)
# Borough selector
# boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
# borough_filter = st.sidebar.selectbox("Select Borough", boroughs)
# Load all data
# Time range selector
time_range = st.sidebar.slider(
    "Select Time Range",
    value=(0, 23),  # Default: 00:00 to 23:59
    min_value=0,
    max_value=23,
    step=1,
    format="%02d:00"
)
time_start = f"{time_range[0]:02d}:00:00"  # Start hour formatted as HH:00:00
time_end = f"{time_range[1]:02d}:59:59"  # End hour formatted as HH:59:59

gdf_data = load_all_gtfs()
gdf_all = pd.concat(gdf_data.values(), ignore_index=True)
# gdf_join = gdf_data[borough_filter]#\
        # .groupby(['route_id']).head(1)
latest_date = get_latest_data_date()

# Date Selector
with col1:
    date_start = st.date_input("Start Date", max_value = latest_date)
with col2:
    date_end = st.date_input("End Date", max_value=latest_date)

# Add a button to trigger the data fetch
if st.sidebar.button("Fetch Data", key="fetch_button"):
    try:
        # Fetch the data
        with st.spinner("Fetching and processing data..."):
            df = fetch_bus_data(
                date_start=date_start.strftime('%Y-%m-%d') if date_start else None,
                date_end=date_end.strftime('%Y-%m-%d') if date_end else None,
                time_start=time_start,
                time_end=time_end
            )
        # Display the results
        # st.header("Results")
        
        # Convert avg_speed to numeric and round to 2 decimal places
        if 'avg_speed' in df.columns:
            df['avg_speed'] = pd.to_numeric(df['avg_speed']).round(2)

        # Display basic statistics
        if not df.empty:
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Speed", f"{df['avg_speed'].mean():.2f} mph")
            with col2:
                st.metric("Fastest Route", f"Route {df.loc[df['avg_speed'].idxmax(), 'route_id']}")
            with col3:
                st.metric("Slowest Route", f"Route {df.loc[df['avg_speed'].idxmin(), 'route_id']}")

            df['avg_speed'] = pd.to_numeric(df['avg_speed'], errors='coerce').round(2)
            gdf_routes = gdf_all.merge(df, how = "left", on = "route_id").dropna() 
            gdf_routes["geometry"] = gdf_routes["geometry"].simplify(0.0001)  # Simplifies geometries for faster rendering
            map_center = gdf_routes.geometry.centroid.unary_union.centroid
            if not gdf_routes.empty:
                st.subheader("Bus Routes Map")
                mapbox_html = render_mapbox_map(gdf_routes)
                components.html(mapbox_html, height=600)
            # Display the full dataset
            st.subheader("Detailed Data")
            st.dataframe(gdf_routes.drop(["geometry"],axis =1))

            # Download button for the data
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name="bus_data.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("No data found for the selected filters.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("Use the filters in the sidebar and click 'Fetch Data' to load bus data.")
