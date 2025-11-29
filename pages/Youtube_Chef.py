import streamlit as st
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="YouTube AI Chef", page_icon="🎥")

st.title("🎥 YouTube to Recipe Converter")
st.markdown("Paste a cooking video link, and I'll extract the recipe AND chat with you about it!")

# --- 1. SETUP & SESSION STATE ---
# We need to store the extracted recipe in memory so the chatbot can access it later.
if "current_video_recipe" not in st.session_state:
    st.session_state.current_video_recipe = None # Will hold the recipe text

# Initialize chat history if not present
if "youtube_chat_history" not in st.session_state:
    st.session_state.youtube_chat_history = []

# Helper to get Video ID
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
                # A. Get Transcript
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                full_text = " ".join([t['text'] for t in transcript_list])
                
                # B. Call Gemini to Extract Recipe
                if "geminiapi" in st.secrets.connections:
                    api_key = st.secrets.connections.geminiapi["GEMINI_API_KEY"]
                    client = genai.Client(api_key=api_key)
                    
                    # We ask for a structured output so it's easy to feed back into the chatbot
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
                    
                    # SAVE TO SESSION STATE (Crucial Step!)
                    st.session_state.current_video_recipe = response.text
                    
                    # Reset chat history for a new video
                    st.session_state.youtube_chat_history = [
                        {"role": "model", "content": "I've analyzed the video! Ask me anything about this recipe."}
                    ]
                    
                else:
                    st.error("API Key missing in secrets.toml")

            except Exception as e:
                st.error(f"Could not process video. (Note: This only works on videos with captions). Error: {e}")

# --- 4. DISPLAY RESULTS & CHATBOT ---
# Only show this section if we have a recipe loaded in memory
if st.session_state.current_video_recipe:
    
    st.divider()
    st.subheader("🍲 The Extracted Recipe")
    st.markdown(st.session_state.current_video_recipe)
    
    st.divider()
    st.header("Ask our AI Chef! 🤖")
    st.markdown("Ask for substitutions, tips, or clarification about the video you just watched.")

    # --- CHATBOT LOGIC ---
    
    # 1. Setup Client (Re-init for chat context)
    try:
        gemini_client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
    except Exception:
        st.stop()

    # 2. Dynamic System Instruction based on the VIDEO recipe
    recipe_context = st.session_state.current_video_recipe
    system_instruction = (
        "Role: You are an expert Thai chef. "
        "Context: The user is asking about a specific recipe derived from a YouTube video. "
        f"Here is the recipe information you extracted earlier: \n\n{recipe_context}\n\n"
        "Task: Answer questions about substitutions, techniques, or details based on this text. "
        "Be polite and helpful."
    )

    # 3. Display Chat History
    for message in st.session_state.youtube_chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    # 4. Handle User Input
    if prompt := st.chat_input('Ask about this video recipe...'):
        
        # User Message
        st.session_state.youtube_chat_history.append({'role':'user','content':prompt})
        with st.chat_message('user'):
            st.write(prompt)
            
        # Model Message
        with st.chat_message('model'):
            # Build history for API
            gemini_history = []
            for message in st.session_state.youtube_chat_history:
                role = "user" if message["role"] == "user" else "model"
                gemini_history.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))

            try:
                # Call API
                response_stream = gemini_client.models.generate_content_stream(
                    model="gemini-2.0-flash-exp", 
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )
                
                # Stream Response
                response_content = st.write_stream(response_stream)
                
                # Save to history
                st.session_state.youtube_chat_history.append({'role':'model','content':response_content})

            except Exception as e:
                st.error(f"Chatbot Error: {e}")