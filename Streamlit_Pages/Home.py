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
import branca.colormap as cm
warnings.filterwarnings("ignore")
# from load_css import local_css

# local_css("style.css")



# Set up the Streamlit page
st.set_page_config(page_title="NYC Bus Data Explorer", layout="wide", menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    })
st.title("NYC Bus Data Explorer")


# Background Image Fix with Text Overlay
page_bg_img = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("https://plus.unsplash.com/premium_photo-1667482654587-e7091bb42e0c?q=80&w=2573&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90bywYWdlfHx8fGVufDB8fHx8fA%3D%3D");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.text-box {
    background: rgba(0, 0, 0, 0.6);  /* Dark semi-transparent background */
    color: white;  /* White text for contrast */
    padding: 20px;
    border-radius: 10px;
    max-width: 100%;
    margin: auto;
    text-align: left;
}
</style>
"""

st.markdown(page_bg_img, unsafe_allow_html=True)

# Text inside a styled div for better readability
st.markdown(
    """
    <div class="text-box">
        <h3>Welcome to the NYC Bus Data Explorer!</h3>
        <p>
        This tool is designed to help you navigate how well New York's buses are performing at stops near you and throughout your neighborhood. 
        Navigate to your neighborhood in the <b>Map</b> tab to see an overview of statistics, which you can toggle on the left-hand side. 
        Navigate to the <b>Act</b> tab to see who you can contact for more information or to have your voice heard in future meetings. 
        Navigate to the <b>Analytics</b> tab for a more detailed breakdown of the most recent bus metrics. 
        </p>
        <p>
        This tool was made in partnership with <a href="https://beta.nyc/" target="_blank" style="color:#FFD700;">BetaNYC</a>, 
        a civic tech organization in the City. Visit their website if you have any questions. 
        </p>
        <p><b>Happy exploring!</b></p>
    </div>
    """,
    unsafe_allow_html=True
)

