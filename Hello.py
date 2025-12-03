import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection
# Import both the renderer and the theme injector
from chat_mode import render_ai_chat, inject_food_theme

st.set_page_config(
    page_title="Best Thai Recipe",
    page_icon="🌶️", # Updated icon to match food theme
)

# --- APPLY VISUAL THEME ---
inject_food_theme()

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

st.write("# Best Thai recipe with any ingredients! 🥘") 
st.sidebar.title("Recipe Book 📖")
st.sidebar.write("Select a dish below:")


st.markdown(
    """
    <div style="background-color: rgba(230, 126, 34, 0.1); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    Our website allows anyone from any part of the world to be able to make Thai cuisine
    , with our AI helper, any ingredients that are Thai but are unable to be found in your countries
    can be substituted with the help of our AI chef guidance!
    <br><br>
    <strong>Select the recipe from our sidebar menu to get started!</strong>
    </div>
    """, unsafe_allow_html=True
)

st.divider()

titles_query = f"""
    SELECT "name(eng)" 
    FROM CSV_FILE
    WHERE "name(eng)" IS NOT NULL
"""
try:
    titles_result = con.execute(titles_query).fetchall()
    titles_list = [row[0] for row in titles_result]
except Exception as e:
    st.error(f"Error reading database: {e}")
    titles_list = []

selected_dish = st.sidebar.selectbox(
    "Dishes",
    options=titles_list
)
with st.sidebar:
    st.page_link(
        "pages/Which_menu_for_you.py",
        label="**Click here to see menu**",
        icon="🍱"
    )

##----Main----##

if selected_dish:
    detail_query = f"""
        SELECT "name(eng)", "condiments", "howto"
        FROM CSV_FILE
        WHERE "name(eng)" = ?
    """
    result = con.execute(detail_query, [selected_dish]).fetchone()
    
    dish_name = ""
    dish_ingredients = ""
    dish_instructions = ""
    
    if result:
        dish_name = result[0]
        dish_ingredients = result[1] if result[1] else "No ingredients listed."
        dish_instructions = result[2] if result[2] else "No instructions available."

        st.header(dish_name)

        st.subheader("🛒 Ingredients")
        if dish_ingredients and dish_ingredients != "No ingredients listed.":
            for line in dish_ingredients.split('\n'):
                line = line.strip()
                if line:
                    st.write(f"- {line}")
        else:
            st.info("No ingredients listed.")

        st.subheader("👨‍🍳 How to make")
        if dish_instructions and dish_instructions != "No instructions available.":
            st.write(dish_instructions)
        else:
            st.info("No instructions available.")

st.divider()

# ==============================================================================
# COMBINED CHAT CODE STARTS HERE
# ==============================================================================

if 'chat_enabled' not in st.session_state:
    st.session_state.chat_enabled = False

if 'recipe_data' not in st.session_state:
    st.session_state.recipe_data = {}

st.session_state.recipe_data = {
    "name": dish_name if selected_dish else "",
    "ingredients": dish_ingredients if selected_dish else "No ingredients selected.",
    "instructions": dish_instructions if selected_dish else "No instructions selected."
}

st.sidebar.divider()
st.sidebar.title("AI Chef Mode 🤖")

st.session_state.chat_enabled = st.sidebar.toggle(
    'Enable AI Chat Assistant',
    value=st.session_state.chat_enabled,
    key="chat_toggle_key"
)

if st.session_state.chat_enabled:
    st.sidebar.info("Chat mode is ON. Scroll down the main page to see the chat window!")

# -----------------------------------------------------------------------------
# 5. CONDITIONAL DISPLAY LOGIC
# -----------------------------------------------------------------------------

if st.session_state.chat_enabled:
    st.markdown("## Ask and extract a Youtube recipe!")
    col1, col2 = st.columns([1, 0.20])
    with col1:
        with st.container(border=True):
                st.page_link(
                    "pages/YouTube_Chef.py", 
                    label="**Click here to ask our AI Chef about substituting ingredients from a video!**", 
                    icon="🎥"
                )
    
    render_ai_chat(st.session_state.recipe_data)
