# -*- coding: utf-8 -*-
"""
Created on Fri Jan 16 23:23:46 2026

@author: ghdor
"""

import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="RoTV Direct",
    page_icon="📺",
    layout="centered"
)

# --- CUSTOM CSS ---
# This centers the images and buttons in the grid columns
st.markdown("""
<style>
    [data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- BACKEND LOGIC ---

@st.cache_data(ttl=3600)
def get_channels_with_logos():
    """Scrapes names, links, and LOGOS using BeautifulSoup."""
    url = "https://rds.live/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    channel_data = []

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Based on standard site structure, we look for the grid items
        # Adjust these selectors if the site changes layout
        items = soup.find_all('div', class_='item-canale')

        for item in items:
            link_tag = item.find('a')
            img_tag = item.find('img')
            # Sometimes the name is hidden in a title attribute or a separate div
            title_div = item.find('div', class_='titlu-canal')
            
            if link_tag and img_tag:
                channel_url = link_tag['href']
                logo_url = img_tag['src']
                
                # Ensure logo URL is absolute
                if logo_url and not logo_url.startswith(('http:', 'https:')):
                    logo_url = "https://rds.live" + logo_url

                # Try to find a name, fallback to the URL slug if needed
                name = "Channel"
                if title_div:
                     name = title_div.get_text(strip=True)
                elif img_tag.get('alt'):
                     name = img_tag.get('alt')
                
                # Filter out unwanted elements (like Facebook links sometimes hidden in grid)
                if "rds.live" in channel_url and name:
                     channel_data.append({
                        'name': name,
                        'url': channel_url,
                        'logo': logo_url
                    })
        return channel_data

    except Exception as e:
        print(f"Scraping error: {e}")
        return []

def get_stream_url(channel_url):
    # (This logic remains unchanged from previous versions)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Referer': channel_url,
        'X-Requested-With': 'XMLHttpRequest'
    }
    session = requests.Session()
    try:
        html = session.get(channel_url, headers=headers).text
        id_match = re.search(r"const\s+postID\s*=\s*['\"](\d+)['\"];", html)
        if not id_match: return None, "Could not find channel ID."
        post_id = id_match.group(1)

        ajax_url = "https://rds.live/wp-admin/admin-ajax.php"
        payload = {'action': 'get_video_source', 'tab': 'server1', 'post_id': post_id}
        api_resp = session.post(ajax_url, headers=headers, data=payload).json()
        
        if api_resp.get('success'):
            return api_resp.get('data'), None
        else:
            return None, "Server blocked the request."
    except Exception as e:
        return None, str(e)

# --- UI LAYOUT ---

# Initialize session state to track selection
if 'selected_channel_url' not in st.session_state:
    st.session_state.selected_channel_url = None
if 'selected_channel_name' not in st.session_state:
    st.session_state.selected_channel_name = None

st.title("📺 TV Romania Direct")

# 1. If a channel is selected, show the player
if st.session_state.selected_channel_url:
    if st.button("⬅️ Back to Channels"):
        # Clear selection to go back to grid
        st.session_state.selected_channel_url = None
        st.session_state.selected_channel_name = None
        st.rerun()
        
    st.header(st.session_state.selected_channel_name)
    with st.spinner("Connecting to signal..."):
        stream_link, error = get_stream_url(st.session_state.selected_channel_url)
        if stream_link:
            st.video(stream_link)
        else:
            st.error(error)

# 2. If no channel is selected, show the grid
else:
    st.write("Tap a logo to watch.")
    channels_data = get_channels_with_logos()

    if not channels_data:
        st.error("Could not load channels. Site might be down.")
    else:
        # --- GRID GENERATION ---
        # How many columns per row (3 works well on mobile)
        cols_per_row = 3
        
        # Loop through data in chunks of 3
        for i in range(0, len(channels_data), cols_per_row):
            # Get the next 3 channels
            row_channels = channels_data[i:i+cols_per_row]
            # Create Streamlit columns
            cols = st.columns(cols_per_row)
            
            for j, channel in enumerate(row_channels):
                with cols[j]:
                    # Display Logo with fixed height so rows align
                    # We use HTML to force height because st.image can vary
                    st.markdown(f"""
                        <div style="display: flex; justify-content: center; align-items: center; height: 80px; overflow: hidden;">
                            <img src="{channel['logo']}" style="max-height: 100%; max-width: 100%; object-fit: contain;">
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # The Button below the logo
                    # We use the channel URL as the unique 'key' for Streamlit
                    if st.button(channel['name'][:15], key=channel['url'], use_container_width=True):
                        st.session_state.selected_channel_url = channel['url']
                        st.session_state.selected_channel_name = channel['name']
                        st.rerun()