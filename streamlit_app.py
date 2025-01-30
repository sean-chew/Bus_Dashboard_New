import streamlit as st
import pandas as pd
import urllib.request
import json
from urllib.parse import urlencode
import warnings
import geopandas as gpd
import folium 
warnings.filterwarnings("ignore")

def fetch_bus_data(route_id=None, date_start=None, date_end=None, borough=None, limit=1000):
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
        where_conditions.append(f'timestamp>="{date_start}T00:00:00"')
    if date_end:
        where_conditions.append(f'timestamp<="{date_end}T23:59:59"')
    
    if where_conditions:
        query_speeds['$where'] = ' AND '.join(where_conditions)
    
    # Fetch data
    url_speeds = BASE_API + urlencode(query_speeds)
    response_speeds = urllib.request.urlopen(url_speeds)
    data_speeds = json.loads(response_speeds.read().decode())
    
    # Convert to DataFrame
    df_speeds = pd.DataFrame(data_speeds)
    return df_speeds

# Set up the Streamlit page
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
        # Convert dates to string format for API
        date_start_str = date_start.strftime('%Y-%m-%d') if date_start else None
        date_end_str = date_end.strftime('%Y-%m-%d') if date_end else None
        
        # Fetch the data
        df = fetch_bus_data(
            date_start=date_start_str,
            date_end=date_end_str,
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
            gdf_routes = gpd.read_file("gdf_join.shp")  # Replace with your actual data source
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
        else:
            st.warning("No data found for the selected filters.")
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("Use the filters in the sidebar and click 'Fetch Data' to load bus data.")

