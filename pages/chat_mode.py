import streamlit as st
from google import genai
from google.genai import types

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
    st.markdown(
        """
        Ask for ingredient substitutions, cooking tips, or anything else about Thai cuisine.
        The AI is currently pre-loaded with the recipe details of **""" 
        + (dish_name if dish_name else "the dish you select in the sidebar") 
        + """**.
        """
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
    system_instruction = (
        "Role: You are an expert Thai chef, specializing in this dish. "
        "Your goal is to guide the user in cooking the selected recipe. "
        f"The recipe name is: **{dish_name}**. "
        f"The ingredients are: **{dish_ingredients}**. "
        f"The instructions are: **{dish_instructions}**. "
        "You must answer questions about ingredient substitutions, cooking techniques, and any related culinary questions. "
        "Be polite, helpful, and answer in English. Constraints: Maintain your chef role."
    )

    # 3. Initialize Chat History in session_state (use a specific key for this component)
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [{"role": "model", "content": "Hello! I am your AI Thai chef. How can I help you with your cooking today?"}]
        
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
                # Correct way to create a Part object
                gemini_history.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))
                
            try:
                # Call the streaming API
                response_stream = gemini_client.models.generate_content_stream(
                    model=GEMINI_MODEL, 
                    contents=gemini_history,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        thinking_config=types.ThinkingConfig(thinking_budget=-1)
                    )
                )
                
                # Use a local variable for accumulating response content
                response_content = ''
                
                # The generator function yields chunks and accumulates the full response
                def stream_and_accumulate(stream_response):
                    nonlocal response_content
                    for chunk in stream_response:
                        text = chunk.text
                        response_content += text
                        yield text
                        
                # Stream the response to the UI
                stream = stream_and_accumulate(response_stream)
                st.write_stream(stream)
                
                # 3. Add final assistant response to history
                st.session_state.chat_messages.append({'role':'model','content':response_content})

            except Exception as e:
                st.error(f"Chatbot Error: {e}")
                st.session_state.chat_messages.pop() # Remove last user message on error