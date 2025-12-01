import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection
from chat_mode import render_ai_chat
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
    ### Or have a Youtube video? Enable AI mode to extract and ask about the recipe!
"""
)

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

# 1. Initialize session state variables if they don't exist
if 'chat_enabled' not in st.session_state:
    st.session_state.chat_enabled = False
# We will use 'recipe_data' to pass the selected dish details to the chat page/component
if 'recipe_data' not in st.session_state:
    st.session_state.recipe_data = {}

# 2. Update recipe data based on selection (from the main logic)
st.session_state.recipe_data = {
    "name": dish_name if selected_dish else "",
    "ingredients": dish_ingredients if selected_dish else "No ingredients selected.",
    "instructions": dish_instructions if selected_dish else "No instructions selected."
}

st.sidebar.divider()
st.sidebar.title("AI Chef Mode 🤖")

# 3. Create the toggle button in the sidebar
st.session_state.chat_enabled = st.sidebar.toggle(
    'Enable AI Chat Assistant',
    value=st.session_state.chat_enabled,
    key="chat_toggle_key"
)

# 4. Logic to display the chat component or redirect (if needed)
if st.session_state.chat_enabled:
    st.sidebar.info("Chat mode is ON. Scroll down the main page to see the chat window!")
    # NOTE: Since you want the chat on the main page, we will call a function 
    # to render the chat when the toggle is ON.

# ==============================================================================
# END OF COMBINED CHAT CODE
# ==============================================================================
if st.session_state.chat_enabled:
    # Pass the recipe data from session state to the chat component
    render_ai_chat(st.session_state.recipe_data)
