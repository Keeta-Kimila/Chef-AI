import streamlit as st
from google import genai
from google.genai import types

def inject_food_theme():
    """
    Injects global CSS for the Food/Recipe Theme.
    This ensures visual uniformity across all pages.
    """
    st.markdown("""
    <style>
        /* IMPORT FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@700;900&family=Lato:wght@400;700&display=swap');

        /* GLOBAL TYPOGRAPHY */
        html, body, [class*="css"] {
            font-family: 'Lato', sans-serif;
        }
        
        /* HEADERS (Menu Style) */
        h1, h2, h3 {
            font-family: 'Merriweather', serif !important;
            color: #D35400 !important; /* Pumpkin Spice Color */
            font-weight: 700 !important;
        }
        
        /* BUTTONS */
        .stButton > button {
            background-color: #E67E22;
            color: white !important;
            border-radius: 12px;
            border: 1px solid #D35400;
            font-family: 'Lato', sans-serif;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #D35400;
            border-color: #A04000;
            transform: scale(1.02);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* INPUT FIELDS */
        .stTextInput > div > div > input, .stSelectbox > div > div > div {
            border-radius: 10px;
            border: 1px solid #F5B041;
            background-color: rgba(255, 255, 255, 0.05); /* Subtle transparency */
        }
        .stTextInput > div > div > input:focus {
            border-color: #D35400;
            box-shadow: 0 0 0 1px #D35400;
        }

        /* SIDEBAR styling */
        [data-testid="stSidebar"] {
            background-color: #FEF9E7; /* Light Cream for Light Mode */
            border-right: 1px solid #F5CBA7;
        }
        /* Dark Mode Sidebar Override */
        @media (prefers-color-scheme: dark) {
            [data-testid="stSidebar"] {
                background-color: #1A1A1A;
                border-right: 1px solid #333;
            }
        }

        /* CARD/CONTAINER STYLING */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
            background-color: rgba(255, 255, 255, 0.02);
            border-radius: 15px;
            padding: 10px;
        }
        
        /* PAGE LINKS (Buttons) */
        a[href] {
            text-decoration: none;
        }
    </style>
    """, unsafe_allow_html=True)

def render_ai_chat(dish_data):
    """
    Renders the AI Chat interface based on the provided recipe data.
    """
    # Apply the theme locally if this function is called alone, 
    # but usually main.py handles the injection. 
    # We leave this specific call out to avoid double injection if main.py does it.
    
    # Configuration for Gemini
    GEMINI_MODEL = "gemini-2.5-flash"
    
    # Access recipe data passed from main.py
    dish_name = dish_data.get("name", "")
    dish_ingredients = dish_data.get("ingredients", "No ingredients selected.")
    dish_instructions = dish_data.get("instructions", "No instructions selected.")

    st.divider()

    st.header("Ask our AI Chef! 🤖")
    st.markdown(
        f"""
        <div style="background-color: rgba(230, 126, 34, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #E67E22;">
        Ask for ingredient substitutions, cooking tips, or anything else about Thai cuisine.
        The AI is currently pre-loaded with the recipe details of <strong>{dish_name if dish_name else "the dish you select in the sidebar"}</strong>.
        </div>
        """, unsafe_allow_html=True
    )
    
    try:
        # 1. Initialize Gemini Client
        gemini_client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
    except (AttributeError, KeyError):
        st.error("Gemini API key not found in secrets. Please configure `st.secrets.connections.geminiapi['GEMINI_API_KEY']`.")
        return # Stop chat rendering on API error
    except Exception as e:
        st.error(f"Failed to initialize Gemini Client: {e}")
        return # Stop chat rendering on other errors


    # 2. Set up System Instruction (Context)
    system_instruction = f"""Context: You are a globally recognized expert Thai chef, specializing in adapting and translating authentic Thai recipes for cooks in other countries. Your primary expertise lies in **substituting hard-to-find ingredients** with readily available international alternatives while preserving the integrity of the dish’s flavor profile (taste, aroma, and texture)."
    Task: Guide the user through the process of preparing and cooking the specified recipe. Provide detailed, insightful culinary advice, and respond comprehensively to all user questions regarding ingredients, techniques, and potential substitutions. You must act as a patient, encouraging, and highly knowledgeable mentor.,
            
    Recipe_Data:
                Name: **{dish_name}**
                Ingredients: **{dish_ingredients}**
                Instructions: **{dish_instructions}**
    Guidelines: **Substitution Protocol:** When a user asks for a substitution, or when you proactively suggest one, you must explicitly state the original, authentic Thai ingredient and its recommended substitute, followed by a brief, specific explanation of *why* the substitute works (e.g., 'substituting palm sugar with brown sugar for its molasses notes and soft texture').,
                **Accuracy and Flavor Integrity:** Only propose substitutions that maintain the essential balance (spicy, sour, sweet, salty) and core character of the Thai dish. If a perfect substitution is impossible, explain the compromise or nearest achievable flavor profile.,
                **Instruction Modification:** If an ingredient substitution necessitates a change to the original cooking instructions (e.g., a change in cooking time or technique), you must detail the revised instruction step clearly to ensure the ‘better version’ of the dish is achieved.,
                **Technique Explanations:** When discussing cooking techniques, use specific, detailed language (e.g., temperature control, oil choice, wok movement) to enhance the user’s understanding.
    Constraints: Maintain the expert Thai chef persona at all times.,
                All responses must be written in English (United Kingdom).,
                Do not fabricate culinary facts, ingredient interactions, or nonexistent techniques (avoiding hallucinations). If you lack sufficient information, state what additional detail is needed.,
                The initial guidance provided must be based specifically on the Recipe_Data provided above, but can be substituted if the recipe does not make sense or is not up to Thai standard.
    """

    # 3. Initialize Chat History
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [{"role": "model", "content": "Hello! I am your personal AI chef. How can I help you with your cooking today?"}]
        
    # Display chat messages from history on app rerun
    for message in st.session_state.chat_messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    if prompt := st.chat_input('Ask Anything..'):
        # 1. User Message Handling
        st.session_state.chat_messages.append({'role':'user','content':prompt})
        with st.chat_message('user'):
            st.write(prompt)
            
        # 2. Model Response Generation
        with st.chat_message('model'):
            # Convert Streamlit history format to Gemini API format
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
