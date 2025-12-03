import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
from chat_mode import render_ai_chat, inject_food_theme

st.set_page_config(page_title="Menu Analyzer", page_icon="📊")

# APPLY THEME
inject_food_theme()

col1, col2 = st.columns([1, 1.95])
with col1:
    with st.container(border=True):
        st.page_link("main.py", label="**Back to Recipe Book**", icon="🏠", use_container_width=True)
st.divider()

# --- 1. SETUP DATABASE CONNECTION ---
@st.cache_resource
def connect_datafood(name):
    mycon = st.connection(name, type=GSheetsConnection)
    return mycon

@st.cache_data
def load_datafood(_con):
    df = _con.read(usecols=[1,2,3,4,5,6,7,8,9])
    return df

@st.cache_resource
def connect_duckdb():
    return duckdb.connect(database=':memory:')

connect_googlesheet = connect_datafood("datafoods")
CSV_FILE = load_datafood(connect_googlesheet)
con = connect_duckdb()

st.title("📊 Ingredient Analyzer")

# --- 2. SIDEBAR SETUP ---
st.sidebar.title("AI Chef Mode 🤖")
show_chat_section = st.sidebar.toggle("Enable AI Chat Assistant", value=False)


# ==============================================================================
# CONTENT SECTION 1: Condiments Bar Plot
# ==============================================================================
st.subheader("1. Ingredient Distribution")

categories = ['Pork', 'Beef', 'Prawn', 'Chicken', 'Fish','Other']
counts = []

for cat in categories:
    query = f"""
        SELECT count(*) FROM CSV_FILE 
        WHERE "{cat}" = 1;
    """
    
    result = con.execute(query).fetchone()
    counts.append(result[0] if result else 0)

# Updated chart colors for theme
fig = go.Figure(data=[go.Bar(
    x=categories,
    y=counts,
    marker_color=['#E74C3C', '#C0392B', '#E67E22', '#F39C12', '#F5B041', '#D35400'] 
)])

# Chart styling based on theme
text_col = "#E0E0E0" if st.session_state.get('dark_mode', False) else "#2C3E50"

fig.update_layout(
    title="Recipe Count by Main Ingredient",
    xaxis_title="Ingredient",
    yaxis_title="Number of Recipes",
    clickmode='event+select',
    font=dict(family="Lato, sans-serif", color=text_col),
    title_font=dict(family="Merriweather, serif", color="#E67E22"),
    paper_bgcolor='rgba(0,0,0,0)', # Transparent background
    plot_bgcolor='rgba(0,0,0,0)'
)

selected_point = st.plotly_chart(fig, use_container_width=True, on_select="rerun")


# ==============================================================================
# CONTENT SECTION 2: Query Table
# ==============================================================================
st.subheader("2. Filtered Recipe List")

selected_category = None

if selected_point and selected_point['selection']['points']:
    selected_category = selected_point['selection']['points'][0]['x']

if selected_category:
    st.info(f"Showing recipes containing: **{selected_category.capitalize()}**")
    table_query = f"""
        SELECT "name(eng)" AS Menu
        FROM CSV_FILE 
        WHERE "{selected_category}" = 1;
    """
else:
    st.write("Displaying all recipes containing the analyzed ingredients (Click a bar above to filter).")
    table_query = """
        SELECT "name(eng)" AS Menu
        FROM CSV_FILE  
    """

try:
    df_result = con.execute(table_query).fetchdf()
    
    # --- FIX: START INDEX FROM 1 ---
    # Pandas defaults to 0, so we just add 1 to the whole index
    df_result.index = df_result.index + 1 
    
    # Display with width="stretch" (fixing the warning you saw earlier)
    st.dataframe(df_result, use_container_width=True)
    
except Exception as e:
    st.error(f"Error fetching data: {e}")


# ==============================================================================
# CONTENT SECTION 3: Chat Interface (Conditional)
# ==============================================================================

if show_chat_section:
    st.divider()
    
    titles_query = 'SELECT "name(eng)" FROM CSV_FILE WHERE "name(eng)" IS NOT NULL'
    try:
        titles_result = con.execute(titles_query).fetchall()
        titles_list = [row[0] for row in titles_result]
    except:
        titles_list = []

    selected_dish_menu = st.selectbox(
        "Select a dish to discuss:",
        options=titles_list,
        index=None,
        placeholder="Choose a recipe..."
    )

    if selected_dish_menu:
        # Reuse logic
        detail_query = 'SELECT "name(eng)", "condiments", "howto" FROM CSV_FILE WHERE "name(eng)" = ?'
        res = con.execute(detail_query, [selected_dish_menu]).fetchone()
        
        dish_data_for_chat = {
            "name": res[0] if res else "",
            "ingredients": res[1] if res else "",
            "instructions": res[2] if res else ""
        }

        render_ai_chat(dish_data_for_chat)

    else:
        st.info("Please select a dish above to start the chat.")

