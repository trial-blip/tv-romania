import streamlit as st
import cloudscraper # <--- The new secret weapon
import re
from bs4 import BeautifulSoup

# --- PAGE CONFIG ---
st.set_page_config(page_title="RoTV Direct", page_icon="📺", layout="centered")

# --- CSS ---
st.markdown("""
<style>
    [data-testid="stImage"] { display: flex; justify-content: center; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- BACKEND LOGIC ---
# Create a scraper instance that mimics a real Chrome browser
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

@st.cache_data(ttl=3600)
def get_channels_with_logos():
    url = "https://rds.live/"
    channel_data = []

    try:
        # Use scraper.get instead of requests.get
        resp = scraper.get(url) 
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.find_all('div', class_='item-canale')

        for item in items:
            link_tag = item.find('a')
            img_tag = item.find('img')
            
            if link_tag and img_tag:
                channel_url = link_tag['href']
                logo_url = img_tag['src']
                if logo_url and not logo_url.startswith(('http:', 'https:')):
                    logo_url = "https://rds.live" + logo_url
                
                name = img_tag.get('alt') or "Channel"
                
                if "rds.live" in channel_url:
                     channel_data.append({'name': name, 'url': channel_url, 'logo': logo_url})
        return channel_data
    except Exception as e:
        print(f"Scraping error: {e}")
        return []

def get_stream_url(channel_url):
    try:
        # Use scraper here too
        html = scraper.get(channel_url).text
        
        id_match = re.search(r"const\s+postID\s*=\s*['\"](\d+)['\"];", html)
        if not id_match: return None, "Channel ID not found (Protection might be active)."
        post_id = id_match.group(1)

        ajax_url = "https://rds.live/wp-admin/admin-ajax.php"
        payload = {'action': 'get_video_source', 'tab': 'server1', 'post_id': post_id}
        
        # Headers are handled automatically by cloudscraper, but we add Referer just in case
        headers = {'Referer': channel_url, 'X-Requested-With': 'XMLHttpRequest'}
        
        api_resp = scraper.post(ajax_url, data=payload, headers=headers).json()
        
        if api_resp.get('success'):
            return api_resp.get('data'), None
        else:
            return None, "Server blocked the video request."
    except Exception as e:
        return None, str(e)

# --- UI ---
if 'selected_channel_url' not in st.session_state:
    st.session_state.selected_channel_url = None
if 'selected_channel_name' not in st.session_state:
    st.session_state.selected_channel_name = None

st.title("📺 TV Romania Direct")

if st.session_state.selected_channel_url:
    if st.button("⬅️ Back to Channels"):
        st.session_state.selected_channel_url = None
        st.rerun()
        
    st.header(st.session_state.selected_channel_name)
    with st.spinner("Connecting..."):
        stream_link, error = get_stream_url(st.session_state.selected_channel_url)
        if stream_link:
            st.video(stream_link)
        else:
            st.error(f"Error: {error}")
else:
    st.write("Tap a logo to watch.")
    channels_data = get_channels_with_logos()
    if not channels_data:
        st.error("Could not load channels. The site blocked the cloud connection.")
        st.info("Note: Free cloud servers are in the USA. If rds.live is 'Romania Only', this web link won't work.")
    else:
        cols_per_row = 3
        for i in range(0, len(channels_data), cols_per_row):
            row_channels = channels_data[i:i+cols_per_row]
            cols = st.columns(cols_per_row)
            for j, channel in enumerate(row_channels):
                with cols[j]:
                    st.markdown(f"""<div style="display: flex; justify-content: center; height: 80px; overflow: hidden;"><img src="{channel['logo']}" style="max-height: 100%; max-width: 100%; object-fit: contain;"></div>""", unsafe_allow_html=True)
                    if st.button(channel['name'][:15], key=channel['url'], use_container_width=True):
                        st.session_state.selected_channel_url = channel['url']
                        st.session_state.selected_channel_name = channel['name']
                        st.rerun()
