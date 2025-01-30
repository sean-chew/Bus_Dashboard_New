import streamlit as st
import pandas as pd
import urllib.request
import json
from urllib.parse import urlencode
import warnings
import folium
from folium import plugins
import geopandas as gpd
warnings.filterwarnings("ignore")

# Function to fetch bus route speed data
def fetch_bus_data(route_id=None, date_start=None, date_end=None, borough=None, limit=1000):
    BASE_API = "https://data.ny.gov/resource/58t6-89vi.json?"
    
    query_speeds = {
        '$select': 'route_id, route_name, AVG(average_road_speed) as avg_speed',
        '$group': 'route_id, route_name',
        '$limit': limit,
        '$order': 'avg_speed'
    }
    
    where_conditions = []
    
    if route_id:
        where_conditions.append(f'route_id="{route_id}"')
    if borough:
        where_conditions.append(f'borough="{borough}"')
    if date_start:
        where_conditions.append(f'timestamp>="{date_start}T00:00:00"')
    if date_end:
        where_conditions.append(f'timestamp<="{date_end}T23:59:59"')
    
    if where_conditions:
        query_speeds['$where'] = ' AND '.join(where_conditions)
    
    url_speeds = BASE_API + urlencode(query_speeds)
    
    try:
        response_speeds = urllib.request.urlopen(url_speeds)
        data_speeds = json.loads(response_speeds.read().decode())
        df_speeds = pd.DataFrame(data_speeds)
    except Exception as e:
        df_speeds = pd.DataFrame()  # Return empty DataFrame on error
        st.error(f"Error fetching data: {str(e)}")
    
    return df_speeds

# Streamlit Page Setup
st.set_page_config(page_title="NYC Bus Data Explorer", layout="wide")
st.title("NYC Bus Route Data Explorer")

# Sidebar Controls
st.sidebar.header("Filters")

# Date Range Selector
col1, col2 = st.sidebar.columns(2)
with col1:
    date_start = st.date_input("Start Date")
with col2:
    date_end = st.date_input("End Date")

# Borough Selector
boroughs = ["All", "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
selected_borough = st.sidebar.selectbox("Select Borough", boroughs)
borough_filter = None if selected_borough == "All" else selected_borough

# Fetch available routes for selection
df_routes = fetch_bus_data(limit=500)  # Get a list of routes

if not df_routes.empty:
    df_routes.drop_duplicates(subset=['route_id', 'route_name'], inplace=True)  
    route_options = ["All Routes"] + df_routes['route_name'].tolist()
    selected_route_name = st.sidebar.selectbox("Select Route", route_options)

    # Get the corresponding route_id if a specific route is selected
    if selected_route_name != "All Routes":
        selected_route_id = df_routes[df_routes['route_name'] == selected_route_name]['route_id'].values[0]
    else:
        selected_route_id = None
else:
    st.sidebar.warning("No routes found.")
    selected_route_id = None

# Number of results limiter
limit = st.sidebar.slider("Number of results", min_value=10, max_value=1000, value=100, step=10)

# Fetch Data on Button Click
if st.sidebar.button("Fetch Data"):
    try:
        date_start_str = date_start.strftime('%Y-%m-%d') if date_start else None
        date_end_str = date_end.strftime('%Y-%m-%d') if date_end else None
        
        df = fetch_bus_data(
            route_id=selected_route_id,
            date_start=date_start_str,
            date_end=date_end_str,
            borough=borough_filter,
            limit=limit
        )
        
        # Display results
        st.header("Results")

        if not df.empty:
            df['avg_speed'] = pd.to_numeric(df['avg_speed']).round(2)  # Convert avg_speed to numeric
            
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Speed", f"{df['avg_speed'].mean():.2f} mph")
            with col2:
                st.metric("Fastest Route", df.loc[df['avg_speed'].idxmax(), 'route_name'])
            with col3:
                st.metric("Slowest Route", df.loc[df['avg_speed'].idxmin(), 'route_name'])
            
            # Display Detailed Data
            st.subheader("Detailed Data")
            st.dataframe(df[['route_id', 'route_name', 'avg_speed']])
            
            # Display Map
            st.subheader("Map Visualization")

            # Assuming gdf is your GeoDataFrame containing route geometries (add this if not already available)
            gdf_routes = gpd.read_file("gdf_join.shp")  # Replace with your actual data source

            # Create the Folium map centered on the average of the route coordinates
            map_center = gdf_routes.geometry.centroid.unary_union.centroid
            folium_map = folium.Map(location=[map_center.y, map_center.x], zoom_start=12)

            # Add routes to the map as lines
            for _, row in gdf_routes.iterrows():
                folium.PolyLine(
                    locations=[(lat, lon) for lon, lat in row.geometry.coords],
                    color="blue",  # You can map this to the route_id or avg_speed if needed
                    weight=3,
                    opacity=0.7,
                    popup=row['route_name']
                ).add_to(folium_map)

            # Display the map in Streamlit
            st.write(folium_map)
            
            # Download button for CSV
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