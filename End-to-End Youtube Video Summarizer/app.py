import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import os
import re
import yt_dlp
from datetime import datetime

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_video_details(youtube_url):
    """Fetches all video details using yt_dlp for reliable extraction."""
    try:
        # Extract Video ID
        video_id_match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', youtube_url)
        if not video_id_match:
            return None
        video_id = video_id_match.group(1)

        # Use yt_dlp for comprehensive data extraction
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'quiet': True,
            'no_warnings': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            # Extract transcript/captions
            subtitles = info.get('subtitles', {}).get('en', [])
            automatic_captions = info.get('automatic_captions', {}).get('en', [])

            # Combine manual and automatic captions
            all_captions = subtitles + automatic_captions
            transcript_text = "\n".join([caption.get('text', '') for caption in all_captions if caption.get('text')])

            if not transcript_text.strip():
                transcript_text = "No transcript available for this video."

            # Extract metadata from yt_dlp info
            return {
                'video_id': video_id,
                'transcript': transcript_text,
                'title': info.get('title', 'Unknown Title'),
                'channel_name': info.get('uploader', 'Unknown Channel'),
                'thumbnail_url': info.get('thumbnail', ''),
                'publish_date': info.get('upload_date', 'N/A'),
                'views': str(info.get('view_count', 'N/A')),
                'likes': str(info.get('like_count', 'N/A'))
            }

    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def generate_summary(video_details):
    prompt = f"""You are an expert video summarizer. Provide a comprehensive summary of this YouTube video.

**Video Details:**
- **Title:** {video_details['title']}
- **Channel:** {video_details['channel_name']}
- **Publish Date:** {video_details['publish_date']}

**Summary Sections:**
1. **Key Topics Covered** (Bullet points)
2. **Main Takeaways** (3-5 important bullet points)
3. **Detailed Summary** (A comprehensive paragraph of 200-300 words)
4. **Key Quotes** (2-3 memorable quotes, if applicable)
5. **Recommendations** (Who should watch this video and why)

Use this transcript as your source:
{video_details['transcript']}"""

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text

def display_results(video_details, summary):
    st.markdown("---")

    if video_details['thumbnail_url']:
        st.image(video_details['thumbnail_url'], use_container_width=True)

    st.markdown(f"#### **Video title:** {video_details['title']}")
    st.markdown(f"**Channel:** {video_details['channel_name']}")
    st.markdown(f"**Views:** {video_details['views']}")
    st.markdown(f"**Likes:** {video_details['likes']}")
    publish_date = video_details['publish_date']
    formatted_date = publish_date if publish_date == 'N/A' else datetime.strptime(publish_date, '%Y%m%d').strftime('%d-%m-%Y')
    st.markdown(f"**Published:** {formatted_date}")

    st.markdown("---")
    st.markdown("### Summary")
    st.markdown(summary)

st.set_page_config(layout="centered", page_title="YouTube Video Summarizer")

# Header with logo and title
col1, col2 = st.columns([0.15, 0.85])

with col1:
    st.image("youtube.png", width=80)

with col2:
    st.markdown("""
    <h1 style="margin: 0px; color: #ffffff; font-size: 2.5em; line-height: 0.5cm;">
        YouTube Video Summarizer
    </h1>
    """, unsafe_allow_html=True)


youtube_url = st.text_input("Enter the YouTube URL and press Summarize")

if st.button("Summarize"):
    if not youtube_url:
        st.warning("Please enter a YouTube URL.")
    else:
        with st.spinner("Fetching details and summarizing..."):
            video_details = get_video_details(youtube_url)
            if video_details:
                summary = generate_summary(video_details)
                display_results(video_details, summary)