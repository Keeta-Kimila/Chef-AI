import streamlit as st
from google import genai
from google.genai import types

def inject_food_theme():
    """
    Injects global CSS for the Food/Recipe Theme and handles Light/Dark mode toggling.
    """
    # --- 1. THEME TOGGLE LOGIC ---
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True # Default to Dark Mode for better initial impression

    with st.sidebar:
        st.session_state.dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)

    # --- 2. DEFINE COLORS BASED ON MODE ---
    if st.session_state.dark_mode:
        # DARK MODE PALETTE
        bg_color = "#121212"            # Deep Dark Background
        sidebar_bg = "#1E1E1E"          # Dark Sidebar
        text_color = "#E0E0E0"          # Light Grey Text (Readable)
        header_color = "#FF9F43"        # Bright Orange for Headers
        
        # Specific fix for Inputs and Cards
        card_bg = "#2C2C2C"             
        input_bg = "#333333"            
        input_border = "#555555"
        
        # Link Colors
        link_text_color = "#FFD700"     # Gold for links/buttons in dark mode
    else:
        # LIGHT MODE PALETTE
        bg_color = "#FFFFFF"
        sidebar_bg = "#FEF9E7"          # Cream Sidebar
        text_color = "#2C3E50"          # Dark Blue-Grey Text
        header_color = "#D35400"        # Pumpkin Spice
        
        card_bg = "#FFF5E6"             # Very Light Orange
        input_bg = "#FFFFFF"
        input_border = "#F5B041"
        
        link_text_color = "#D35400"     # Dark Orange for links

    # --- 3. INJECT STRONGER DYNAMIC CSS ---
    st.markdown(f"""
    <style>
        /* IMPORT FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@700;900&family=Lato:wght@400;700&display=swap');

        /* MAIN APP COLORS */
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
            font-family: 'Lato', sans-serif;
        }}
        
        /* HEADERS */
        h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
            font-family: 'Merriweather', serif !important;
            color: {header_color} !important;
        }}
        
        /* TEXT COLOR OVERRIDES (Fixes grey text in dark mode) */
        p, .stMarkdown, .stText, label {{
            color: {text_color} !important;
        }}

        /* --- FIX: PAGE LINK / BUTTON TEXT VISIBILITY --- */
        /* This specifically targets the text inside st.page_link to ensure it's visible */
        .stPageLink a p {{
            color: {link_text_color} !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
        }}
        /* Icon color inside page link */
        .stPageLink a span {{
             color: {text_color} !important;
        }}
        /* Hover effect for page links */
        .stPageLink a:hover {{
            background-color: rgba(230, 126, 34, 0.2) !important;
            border-radius: 8px;
        }}

        /* --- FIX: INPUT FIELDS (Youtube & Chat) --- */
        /* Forces background and text color for inputs */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {input_border} !important;
        }}
        /* Placeholder text color */
        ::placeholder {{
            color: {text_color} !important;
            opacity: 0.5;
        }}

        /* SIDEBAR */
        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg};
            border-right: 1px solid {input_border};
        }}
        
        /* CARDS / CONTAINERS */
        div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {{
            background-color: {card_bg};
            border-radius: 12px;
            border: 1px solid {input_border};
            padding: 15px;
        }}
        
        /* BUTTONS */
        .stButton > button {{
            background-color: #E67E22;
            color: white !important;
            border: none;
            border-radius: 8px;
            font-weight: bold;
        }}
        .stButton > button:hover {{
            background-color: #D35400;
        }}
    </style>
    """, unsafe_allow_html=True)

def render_ai_chat(dish_data):
    """
    Renders the AI Chat interface based on the provided recipe data.
    """
    # Configuration for Gemini
    GEMINI_MODEL = "gemini-2.5-flash"
    
    # Access recipe data passed from main.py
    dish_name = dish_data.get("name", "")
    dish_ingredients = dish_data.get("ingredients", "No ingredients selected.")
    dish_instructions = dish_data.get("instructions", "No instructions selected.")

    st.divider()

    st.header("Ask our AI Chef! 🤖")
    
    # Dynamic styling for the context box based on theme
    box_bg = "#2C2C2C" if st.session_state.get('dark_mode', False) else "rgba(230, 126, 34, 0.1)"
    box_border = "#E67E22"
    text_col = "#E0E0E0" if st.session_state.get('dark_mode', False) else "#2C3E50"

    st.markdown(
        f"""
        <div style="background-color: {box_bg}; padding: 15px; border-radius: 10px; border-left: 5px solid {box_border}; color: {text_col};">
        Ask for ingredient substitutions, cooking tips, or anything else about Thai cuisine.
        The AI is currently pre-loaded with the recipe details of <strong>{dish_name if dish_name else "the dish you select in the sidebar"}</strong>.
        </div>
        """, unsafe_allow_html=True
    )
    
    try:
        gemini_client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
    except (AttributeError, KeyError):
        st.error("Gemini API key not found in secrets.")
        return 
    except Exception as e:
        st.error(f"Failed to initialize Gemini Client: {e}")
        return 


    system_instruction = f"""Context: You are a globally recognized expert Thai chef... (Instruction Logic Remains Same) ...
    Recipe_Data:
                Name: **{dish_name}**
                Ingredients: **{dish_ingredients}**
                Instructions: **{dish_instructions}**
    Guidelines: ... (Same) ...
    """

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [{"role": "model", "content": "Hello! I am your personal AI chef. How can I help you with your cooking today?"}]
        
    for message in st.session_state.chat_messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    if prompt := st.chat_input('Ask Anything..'):
        st.session_state.chat_messages.append({'role':'user','content':prompt})
        with st.chat_message('user'):
            st.write(prompt)
            
        with st.chat_message('model'):
            gemini_history = []
            for message in st.session_state.chat_messages:
                role = "user" if message["role"] == "user" else "model"
                gemini_history.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))
                
            try:
                response_stream = gemini_client.models.generate_content_stream(
                    model=GEMINI_MODEL, 
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        thinking_config=types.ThinkingConfig(thinking_budget=-1)
                    )
                )
                
                response_content = ''
                
                def stream_and_accumulate(stream_response):
                    nonlocal response_content
                    for chunk in stream_response:
                        text = chunk.text
                        response_content += text
                        yield text
                        
                stream = stream_and_accumulate(response_stream)
                st.write_stream(stream)
                
                st.session_state.chat_messages.append({'role':'model','content':response_content})

            except Exception as e:
                st.error(f"Chatbot Error: {e}")
                st.session_state.chat_messages.pop()
