import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Best Thai Recipe",
    page_icon="👋",
)

@st.cache_resource
def connect_datafood(name):
    mycon = st.connection(name, type=GSheetsConnection)
    return mycon
@st.cache_data
def load_datafood(_con):
    df = _con.read(usecols=[1,2,3])
    return df
@st.cache_resource
def connect_duckdb():
    return duckdb.connect(database=':memory:')
connect_googlesheet = connect_datafood("datafoods")
CSV_FILE = load_datafood(connect_googlesheet)
con = connect_duckdb()

st.write("# Best Thai recipe with any ingredients! 👋")
st.sidebar.title("Recipe Book 📖")
st.sidebar.write("Select a dish below:")


st.markdown(
    """
    Our website allows anyone from any part of the world to be able to make Thai cuisine
    , with our AI helper, any ingredients that are Thai but are unable to be found in your countries
    can be substituted with the help of our AI chef guidance!
    **Select the recipe from our sidebar menu** to get started!
    ### Have recipe from a Youtube video but no ingredients?
"""
)

# THIS IS THE NEW LINKING CODE
st.page_link("pages/YouTube_Chef.py", label="Click here to ask our AI Chef about substituting ingredients from a video!", icon="🎥")

st.divider()

titles_query = f"""
    SELECT "name(eng)" 
    FROM CSV_FILE
    WHERE "name(eng)" IS NOT NULL
"""
try:
    titles_result = con.execute(titles_query).fetchall()
    # Flatten list of tuples [('Dish A',), ('Dish B',)] -> ['Dish A', 'Dish B']
    titles_list = [row[0] for row in titles_result]
except Exception as e:
    st.error(f"Error reading database: {e}")
    titles_list = []

selected_dish = st.sidebar.selectbox(
    "Dishes",
    options=titles_list
)

##----Main----##

if selected_dish:
    # Query: Get ingredients and instructions for the specific dish
    detail_query = f"""
        SELECT "name(eng)", "condiments", "howto"
        FROM CSV_FILE
        WHERE "name(eng)" = ?
    """
    # We pass [selected_dish] as a parameter to prevent SQL injection/formatting errors
    result = con.execute(detail_query, [selected_dish]).fetchone()
    
    # Initialize variables for chat system instruction later
    dish_name = ""
    dish_ingredients = ""
    dish_instructions = ""
    
    if result:
        dish_name = result[0]
        dish_ingredients = result[1] if result[1] else "No ingredients listed."
        dish_instructions = result[2] if result[2] else "No instructions available."

        # --- Display Title ---
        st.header(dish_name)

        # --- Display Ingredients ---
        st.subheader("🛒 Ingredients")
        # Your CSV uses newlines to separate ingredients, so we split by \n
        if dish_ingredients and dish_ingredients != "No ingredients listed.":
            for line in dish_ingredients.split('\n'):
                line = line.strip()
                if line:  # Only display non-empty lines
                    st.write(f"- {line}")
        else:
            st.info("No ingredients listed.")

        # --- Display Instructions ---
        st.subheader("👨‍🍳 How to make")
        # Note: The 'howto' column in your current CSV seems to be in Thai.
        if dish_instructions and dish_instructions != "No instructions available.":
            st.write(dish_instructions)
        else:
            st.info("No instructions available.")

# ==============================================================================
# COMBINED CHAT CODE STARTS HERE
# ==============================================================================

st.divider()

st.header("Ask our AI Chef! 🤖")
st.markdown(
    """
    Ask for ingredient substitutions, cooking tips, or anything else about Thai cuisine.
    The AI is currently pre-loaded with the recipe details of **""" 
    + (dish_name if selected_dish else "the dish you select in the sidebar") 
    + """**.
    """
)

# Configuration for Gemini
GEMINI_MODEL = "gemini-2.5-flash"
try:
    # 1. Initialize Gemini Client
    gemini_client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
except (AttributeError, KeyError):
    st.error("Gemini API key not found in secrets. Please configure `st.secrets.connections.geminiapi['GEMINI_API_KEY']`.")
    st.stop()
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.stop()


# 2. Set up System Instruction (Context)
# The system instruction is dynamic based on the selected dish's details
system_instruction = (
    "Role: You are an expert Thai chef, specializing in this dish. "
    "Your goal is to guide the user in cooking the selected recipe. "
    f"The recipe name is: **{dish_name}**. "
    f"The ingredients are: **{dish_ingredients}**. "
    f"The instructions are: **{dish_instructions}**. "
    "You must answer questions about ingredient substitutions, cooking techniques, and any related culinary questions. "
    "Be polite, helpful, and answer in English. Constraints: Maintain your chef role."
)

# 3. Initialize Chat History in session_state
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
            # Gemini API uses 'role: user' and 'role: model'
            role = "user" if message["role"] == "user" else "model"
            
            # --- FIX APPLIED HERE ---
            # Correctly create a types.Part object by passing 'text' keyword argument
            # types.Part.from_text() is incorrect and causes the TypeError.
            gemini_history.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))
            
            # Alternative (simpler) way to write the same line, often used in chat apps:
            # gemini_history.append({"role": role, "parts": [{"text": message["content"]}]})
            
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
            # Using a function to stream and accumulate
            def stream_and_accumulate(stream_response):
                global response_content
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

# ==============================================================================
# END OF COMBINED CHAT CODE
# ==============================================================================
