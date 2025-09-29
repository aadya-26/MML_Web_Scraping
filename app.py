import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="NYC Museum Exhibitions", layout="wide")

st.title("🗽NYC Museum Exhibitions Explorer")
st.markdown("Explore exhibitions, search by keyword, and view word clouds.")

# Load and process data
df = pd.read_csv("nyc_museums_20250929_002923.csv")
# Clear Met's dates and sort Guggenheim first
df.loc[df['museum'] == 'The Met', 'date'] = ''
df['sort_order'] = df['museum'].map({'Guggenheim': 0, 'The Met': 1})
df = df.sort_values('sort_order').drop('sort_order', axis=1).reset_index(drop=True)

st.success(f"Loaded {len(df)} exhibitions.")

# Search/filter
keyword = st.text_input("🔍 Search exhibitions by keyword (title/description):")
if keyword:
    mask = df['title'].str.contains(keyword, case=False, na=False) | df['description'].str.contains(keyword, case=False, na=False)
    filtered_df = df[mask]
    st.write(f"Found {len(filtered_df)} matching exhibitions.")
else:
    filtered_df = df

# Word clouds side by side
st.subheader("☁️ Exhibition Word Clouds")

# Custom stopwords for museum exhibitions
custom_stopwords = set(['null','the','of','and','a','in','to','is','for','on','with','by','as','at','an','from','that','this','it'])

col1, col2 = st.columns(2)

# Title word cloud - Enhanced
with col1:
    st.markdown("### Exhibition Titles")
    title_text = " ".join(filtered_df['title'].dropna().astype(str))
    if title_text:
        title_wc = WordCloud(
            width=1200,
            height=600,
            background_color="#1a1a2e",  # Dark blue background
            colormap="twilight_shifted",  # More artistic color palette
            max_words=150,
            prefer_horizontal=0.6,
            collocations=False,
            min_font_size=12,
            max_font_size=120,
            relative_scaling=0.5,  # Better size distribution
            stopwords=custom_stopwords,
            contour_width=1,
            contour_color='#16213e'
        ).generate(title_text)
        
        fig1, ax1 = plt.subplots(figsize=(12, 6), facecolor='#1a1a2e')
        ax1.imshow(title_wc, interpolation="bilinear")
        ax1.axis("off")
        ax1.set_facecolor('#1a1a2e')
        plt.tight_layout(pad=0)
        st.pyplot(fig1)
        plt.close(fig1)

# Description word cloud - Enhanced
with col2:
    st.markdown("### Exhibition Descriptions")
    desc_text = " ".join(filtered_df['description'].dropna().astype(str))
    if desc_text:
        desc_wc = WordCloud(
            width=1200,
            height=600,
            background_color="#0f3460",  # Deep blue background
            colormap="cool",  # Cool artistic colors
            max_words=150,
            prefer_horizontal=0.6,
            collocations=False,
            min_font_size=12,
            max_font_size=120,
            relative_scaling=0.5,
            stopwords=custom_stopwords,
            contour_width=1,
            contour_color='#16213e'
        ).generate(desc_text)
        
        fig2, ax2 = plt.subplots(figsize=(12, 6), facecolor='#0f3460')
        ax2.imshow(desc_wc, interpolation="bilinear")
        ax2.axis("off")
        ax2.set_facecolor('#0f3460')
        plt.tight_layout(pad=0)
        st.pyplot(fig2)
        plt.close(fig2)

# Table of results
st.subheader("📋 Exhibition List")
st.dataframe(
    filtered_df[["museum", "title", "date", "url", "description"]], 
    use_container_width=True,
    column_config={
        "url": st.column_config.LinkColumn("Exhibition Link"),
        "title": st.column_config.TextColumn("Exhibition Title", width="large"),
        "description": st.column_config.TextColumn("Description", width="large"),
    }
)

# Download filtered data
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered data as CSV", csv, "filtered_exhibitions.csv", "text/csv")