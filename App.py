import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import tempfile
from deep_translator import GoogleTranslator
import fpdf  # PDF Support
from textblob import TextBlob  # Sentiment Analysis
import json  # Export Chapters as JSON
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0  # Ensures consistent results

# Load environment variables
load_dotenv()

# Set up Google Gemini API with FREE MODEL
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("❌ Google API Key not found! Please set it in your .env file.")
else:
    genai.configure(api_key=API_KEY)

# Use "gemini-1.5-flash" instead of "gemini-pro"
MODEL_NAME = "gemini-1.5-flash"  # ✅ FREE Model

prompt = """You are a YouTube video summarizer. You will be taking the transcript text
and summarizing the entire video and providing the important summary in points
within 250 words. Please provide the summary of the text given here:  """

# Extract transcript
def extract_transcript_details(youtube_video_url):
    try:
        if "watch?v=" in youtube_video_url:
            video_id = youtube_video_url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_video_url:
            video_id = youtube_video_url.split("youtu.be/")[1].split("?")[0]
        else:
            return None, "❌ Invalid YouTube URL format."

        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([i["text"] for i in transcript_text])
        return transcript, None

    except Exception as e:
        return None, f"❌ Error: {str(e)}"

# Generate AI Summary
def generate_gemini_content(transcript_text, prompt):
    try:
        model = genai.GenerativeModel(MODEL_NAME)  # ✅ FREE Model
        response = model.generate_content(prompt + transcript_text)
        return response.text
    except Exception as e:
        return f"❌ Google Gemini API Error: {str(e)}"

# Translation
def translate_summary(text, lang):
    try:
        lang_code = {"English": "en", "Hindi": "hi", "Spanish": "es", "French": "fr"}
        if lang not in lang_code:
            return "❌ Unsupported language selected."
        translated_text = GoogleTranslator(source="auto", target=lang_code[lang]).translate(text)
        return translated_text
    except Exception as e:
        return f"❌ Translation Error: {str(e)}"

# PDF Generator
def generate_pdf(summary_text):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(190, 10, summary_text)
    pdf_path = "summary.pdf"
    pdf.output(pdf_path)
    return pdf_path

# Text-to-Speech (TTS)
def text_to_speech(summary_text):
    tts = gTTS(summary_text)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_file.name)
    return temp_file.name

# Generate Video Chapters
def generate_video_chapters(transcript_text):
    words = transcript_text.split()
    chapters = []
    for i in range(0, len(words), 50):  # Every 50 words = New Chapter
        time_min = (i // 150)  # Approx time (1 min = 150 words)
        chapters.append(f"📌 {time_min:02d}:00 - {' '.join(words[i:i+50])}...")
    return "\n".join(chapters)

# Sentiment Analysis
def analyze_sentiment(transcript_text):
    analysis = TextBlob(transcript_text)
    sentiment = "Positive" if analysis.sentiment.polarity > 0 else "Negative" if analysis.sentiment.polarity < 0 else "Neutral"
    return sentiment

# Language Detection
def detect_language(transcript_text):
    return detect(transcript_text)

# Streamlit UI
st.title("▶️YouTube Insight.AI👨‍💻")
st.caption("🤖 Transform YouTube transcripts into valuable insights with AI!🧠")
youtube_link = st.text_input("🎥 Enter YouTube Video Link:")

if youtube_link:
    try:
        video_id = youtube_link.split("watch?v=")[1].split("&")[0] if "watch?v=" in youtube_link else youtube_link.split("youtu.be/")[1].split("?")[0]
        st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)
    except:
        st.warning("Invalid YouTube link format. Please check the URL.")

# Store transcript_text in session state
if st.button("📝 Get Detailed Notes"):
    transcript_text, error = extract_transcript_details(youtube_link)

    if error:
        st.error(error)
    elif transcript_text:
        st.session_state.transcript_text = transcript_text  # Save to session state
        summary = generate_gemini_content(transcript_text, prompt)
        if "❌ Google Gemini API Error" in summary:
            st.error(summary)
        else:
            st.markdown("## 📝 Detailed Notes:")
            st.write(summary)

            # 🎬 Auto-Generated Video Chapters
            chapters = generate_video_chapters(transcript_text)
            st.markdown("## 🎬 Auto-Generated Video Chapters:")
            st.write(chapters)

            # 🌍 Multi-Language Translation
            selected_lang = st.selectbox("🌍 Translate Summary To:", ["English", "Hindi", "Spanish", "French"])
            if st.button("🌍 Translate Summary"):
                if "summary" not in st.session_state:
                    st.session_state.summary = summary  # Save summary to session state
                translated_summary = translate_summary(st.session_state.summary, selected_lang)
                if "❌" in translated_summary:
                    st.error(translated_summary)  # Display error if translation fails
                else:
                    st.markdown(f"## 🌍 Summary in {selected_lang}:")
                    st.write(translated_summary)

            # 🎧 AI Voice Summary
            audio_file = text_to_speech(summary)
            st.audio(audio_file, format="audio/mp3")

            # 📄 Download as TXT & PDF
            st.download_button("📥 Download as TXT", summary, file_name="summary.txt")
            pdf_path = generate_pdf(summary)
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("📄 Download as PDF", pdf_file, file_name="summary.pdf")

# Summarization Length Selector
summary_length = st.radio("Select Summary Length:", ["Short", "Medium", "Long"])

def generate_custom_summary(transcript_text, length):
    length_prompt = {
        "Short": "Summarize the text in 100 words.",
        "Medium": "Summarize the text in 250 words.",
        "Long": "Summarize the text in 500 words."
    }
    return generate_gemini_content(transcript_text, length_prompt[length])

if st.button("📝 Generate Custom Summary"):
    if "transcript_text" in st.session_state:  # Check if transcript_text exists in session state
        transcript_text = st.session_state.transcript_text
        custom_summary = generate_custom_summary(transcript_text, summary_length)
        st.markdown("## 📝 Custom Summary:")
        st.write(custom_summary)
    else:
        st.error("❌ Please generate the transcript first by clicking '📝 Get Detailed Notes'.")

# Use transcript_text from session state for sentiment analysis
if st.button("📊 Analyze Sentiment"):
    if "transcript_text" in st.session_state:
        transcript_text = st.session_state.transcript_text
        sentiment = analyze_sentiment(transcript_text)
        st.markdown(f"## Sentiment Analysis: {sentiment}")
    else:
        st.error("❌ Please generate the transcript first by clicking '📝 Get Detailed Notes'.")

# Transcript Search
search_query = st.text_input("🔍 Search in Transcript:")

if search_query:
    if "transcript_text" in st.session_state:  # Check if transcript_text exists in session state
        transcript_text = st.session_state.transcript_text
        results = [line for line in transcript_text.split(". ") if search_query.lower() in line.lower()]
        st.markdown("## 🔍 Search Results:")
        st.write("\n".join(results) if results else "No results found.")
    else:
        st.error("❌ Please generate the transcript first by clicking '📝 Get Detailed Notes'.")

# Export Chapters as JSON
if st.button("📤 Export Chapters as JSON"):
    if "transcript_text" in st.session_state:
        transcript_text = st.session_state.transcript_text
        chapters = generate_video_chapters(transcript_text)
        chapters_json = json.dumps({"chapters": chapters.split("\n")}, indent=4)
        st.download_button("📥 Download Chapters JSON", chapters_json, file_name="chapters.json")

# Dark Mode Toggle in Sidebar
dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode")

if dark_mode:
    st.markdown(
        """
        <style>
        body {
            background-color: #121212;
            color: white;
        }
        .stButton>button {
            background-color: #444444;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <style>
        body {
            background-color: white;
            color: black;
        }
        .stButton>button {
            background-color: #f0f0f0;
            color: black;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Theme Selection in Sidebar
theme_mode = st.sidebar.selectbox("🌈 Select App Theme:", ["Light Mode", "Dark Mode"])

if theme_mode == "Dark Mode":
    st.markdown(
        """
        <style>
        body {
            background-color: #121212;
            color: white;
        }
        .stButton>button {
            background-color: #444444;
            color: white;
        }
        .stTextInput>div>div>input {
            background-color: #333333;
            color: white;
        }
        .stSelectbox>div>div>div>div {
            background-color: #333333;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
elif theme_mode == "Light Mode":
    st.markdown(
        """
        <style>
        body {
            background-color: white;
            color: black;
        }
        .stButton>button {
            background-color: #f0f0f0;
            color: black;
        }
        .stTextInput>div>div>input {
            background-color: white;
            color: black;
        }
        .stSelectbox>div>div>div>div {
            background-color: white;
            color: black;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

AI_path = "AI.png"  # Ensure this file is in the same directory as your script
if os.path.exists(AI_path):
    st.sidebar.image(AI_path)
else:
    st.sidebar.warning("AI.png file not found. Please check the file path.")

image_path = "image.png"  # Ensure this file is in the same directory as your script
if os.path.exists(image_path):
    st.sidebar.image(image_path)
else:
    st.sidebar.warning("image.png file not found. Please check the file path.")
    
    
# Sidebar Navigation
with st.sidebar:
    st.header("⚙ App Features")

    tab_selection = st.radio("Select a Feature:", [
        "🏠 Home",
        "📝 Get Detailed Notes",
        "🌍 Translate Summary",
        "🎧 AI Voice Summary",
        "📄 Download Summary",
        "📊 Analyze Sentiment",
        "🔍 Search in Transcript",
        "📤 Export Chapters as JSON",
        "🌙 Dark Mode",
        "🌈 Theme Selection",
        "🌍 Detect Transcript Language",
    ])
    
    
    st.markdown("👨👨‍💻Developer:- Abhishek💖Yadav")
    
    developer_path = "pic.jpg"  # Ensure this file is in the same directory as your script
    try:
        st.sidebar.image(developer_path)
    except FileNotFoundError:
        st.sidebar.warning("pic.jpg file not found. Please check the file path.")
