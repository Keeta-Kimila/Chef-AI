import streamlit as st
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="YouTube AI Chef", page_icon="🎥")

# --- APPLY VISUAL THEME (Local Injection for Standalone Safety) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@700;900&family=Lato:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Lato', sans-serif; }
    h1, h2, h3 { font-family: 'Merriweather', serif !important; color: #D35400 !important; font-weight: 700 !important; }
    .stButton > button { background-color: #E67E22; color: white !important; border-radius: 12px; border: 1px solid #D35400; font-family: 'Lato', sans-serif; font-weight: bold; }
    .stButton > button:hover { background-color: #D35400; transform: scale(1.02); }
    .stTextInput > div > div > input { border-radius: 10px; border: 1px solid #F5B041; }
    [data-testid="stSidebar"] { background-color: #FEF9E7; border-right: 1px solid #F5CBA7; }
    @media (prefers-color-scheme: dark) { [data-testid="stSidebar"] { background-color: #1A1A1A; border-right: 1px solid #333; } }
</style>
""", unsafe_allow_html=True)

# Add a button to go back home
col1, col2 = st.columns([1, 2])
with col1:
    with st.container(border=True):
        st.page_link("main.py", label="**Back to Recipe Book**", icon="🏠", width="stretch")
st.divider()

st.title("🎥 YouTube to Recipe Converter")
st.markdown(
    """
    <div style="background-color: rgba(230, 126, 34, 0.1); padding: 15px; border-radius: 10px;">
    Paste a cooking video link below, and I'll extract the recipe AND chat with you about it!
    </div>
    """, unsafe_allow_html=True
)

# --- 1. SETUP & SESSION STATE ---
if "current_video_recipe" not in st.session_state:
    st.session_state.current_video_recipe = None 

if "youtube_chat_history" not in st.session_state:
    st.session_state.youtube_chat_history = []

def get_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
    return None

# --- 2. INPUT SECTION ---
video_url = st.text_input("Paste YouTube Link here:", placeholder="https://www.youtube.com/watch?v=...")

# --- 3. PROCESS VIDEO (The Extraction Phase) ---
if st.button("Extract Recipe 👨‍🍳") and video_url:
    video_id = get_video_id(video_url)
    
    if not video_id:
        st.error("Invalid YouTube URL. Please try again.")
    else:
        with st.spinner("Watching video and taking notes..."):
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['th', 'en'])
                full_text = " ".join([t['text'] for t in transcript_list])
                
                if "geminiapi" in st.secrets.connections:
                    api_key = st.secrets.connections.geminiapi["GEMINI_API_KEY"]
                    client = genai.Client(api_key=api_key)
                    
                    sys_instruct = (
                        "Role: You are an expert Chef. "
                        "Task: Read the following video transcript and extract the recipe. "
                        "Output Format: Please provide a clear title, then a list of Ingredients, then Instructions."
                    )
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"Here is the video transcript: {full_text}",
                        config=types.GenerateContentConfig(
                            system_instruction=sys_instruct
                        ),
                    )
                    
                    st.session_state.current_video_recipe = response.text
                    
                    st.session_state.youtube_chat_history = [
                        {"role": "model", "content": "I've analyzed the video! Ask me anything about this recipe."}
                    ]
                    
                else:
                    st.error("API Key missing in secrets.toml")

            except Exception as e:
                st.error(f"Could not process video. (Note: This only works on videos with captions). Error: {e}")

# --- 4. DISPLAY RESULTS & CHATBOT ---
if st.session_state.current_video_recipe:
    
    st.divider()
    st.subheader("🍲 The Extracted Recipe")
    st.markdown(st.session_state.current_video_recipe)
    
    st.divider()
    st.header("Ask our AI Chef! 🤖")
    st.markdown("Ask for substitutions, tips, or clarification about the video you just watched.")

    # --- CHATBOT LOGIC ---
    try:
        gemini_client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
    except Exception:
        st.stop()

    recipe_context = st.session_state.current_video_recipe
    system_instruction = (
        "Role: You are an expert Thai chef. "
        "Context: The user is asking about a specific recipe derived from a YouTube video. "
        f"Here is the recipe information you extracted earlier: \n\n{recipe_context}\n\n"
        "Task: Answer questions about substitutions, techniques, or details based on this text. "
        "Be polite and helpful."
    )

    for message in st.session_state.youtube_chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    if prompt := st.chat_input('Ask about this video recipe...'):
        
        st.session_state.youtube_chat_history.append({'role':'user','content':prompt})
        with st.chat_message('user'):
            st.write(prompt)
            
        with st.chat_message('model'):
            gemini_history = []
            for message in st.session_state.youtube_chat_history:
                role = "user" if message["role"] == "user" else "model"
                gemini_history.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))

            try:
                response_stream = gemini_client.models.generate_content_stream(
                    model="gemini-2.5-flash", 
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )
                
                def stream_parser(stream):
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text

                response_content = st.write_stream(stream_parser(response_stream))
                    
                st.session_state.youtube_chat_history.append({'role':'model','content':response_content})

            except Exception as e:
                st.error(f"Chatbot Error: {e}")
