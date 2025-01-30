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
import folium
import shapely as sp
import streamlit.components.v1 as components
warnings.filterwarnings("ignore")

# URL to the GTFS data
url = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_b.zip"

# Function to download and extract the ZIP file from the URL
def fetch_and_extract_gtfs(url):
    # Download the file from the URL
    response = requests.get(url)
    
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Create a BytesIO object from the response content
        zip_file = io.BytesIO(response.content)
        
        # Extract the ZIP file in memory
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # List all files in the ZIP
            # zip_ref.printdir()

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
df_shapes, df_trips = fetch_and_extract_gtfs(url)
df_shapes['shape_pt_sequence'] = pd.to_numeric(df_shapes['shape_pt_sequence'])

# Sort data to ensure points are in correct order
df_shapes = df_shapes.sort_values(by=['shape_id', 'shape_pt_sequence'])
# Group by shape_id and create LineString geometry
lines = df_shapes.groupby('shape_id').apply(
    lambda x: sp.geometry.LineString(x[['shape_pt_lon', 'shape_pt_lat']].values)
).reset_index(name='geometry')

# # Convert to GeoDataFrame
gdf = gpd.GeoDataFrame(lines, geometry='geometry', crs="EPSG:4326")  # WGS 84 CRS
gdf_join = gdf.merge(df_trips, on='shape_id', how='left')

# Streamlit page setup
st.set_page_config(page_title="NYC Bus Data Explorer", layout="wide")
st.title("NYC Bus Data Explorer")

# Sidebar controls
st.sidebar.header("Filters")

# Date range selector
col1, col2 = st.sidebar.columns(2)
with col1:
    date_start = st.date_input("Start Date")
with col2:
    date_end = st.date_input("End Date")

# Borough selector
boroughs = ["All", "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
selected_borough = st.sidebar.selectbox("Select Borough", boroughs)

# Convert borough "All" to None for the API
borough_filter = None if selected_borough == "All" else selected_borough

# Number of results limiter
limit = st.sidebar.slider("Number of results", min_value=10, max_value=1000, value=100, step=10)

# Add a button to trigger the data fetch
if st.sidebar.button("Fetch Data"):
    try:
        # Fetch the data
        df = fetch_bus_data(
            date_start=date_start.strftime('%Y-%m-%d') if date_start else None,
            date_end=date_end.strftime('%Y-%m-%d') if date_end else None,
            borough=borough_filter,
            limit=limit
        )

        # Display the results
        st.header("Results")

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

            # Display the full dataset
            st.subheader("Detailed Data")
            st.dataframe(df)

            # Download button for the data
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name="bus_data.csv",
                mime="text/csv"
            )

            st.subheader("Map Visualization")
            gdf_routes = gdf_join  # Replace with your actual data source
            map_center = gdf_routes.geometry.centroid.unary_union.centroid
            folium_map = folium.Map(location=[map_center.y, map_center.x], zoom_start=12)

            # Add routes to the map as lines
            for _, row in gdf_routes.iterrows():
                folium.PolyLine(
                    locations=[(lat, lon) for lon, lat in row.geometry.coords],
                    color="blue",  # You can map this to the route_id or avg_speed if needed
                    weight=3,
                    opacity=0.7
                ).add_to(folium_map)

            # Display the map as HTML in Streamlit
            folium_map_html = folium_map._repr_html_()  # Convert to HTML
            components.html(folium_map_html, height=600)

        else:
            st.warning("No data found for the selected filters.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("Use the filters in the sidebar and click 'Fetch Data' to load bus data.")
