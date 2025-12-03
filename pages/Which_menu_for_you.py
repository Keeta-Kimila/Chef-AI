import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
from google import genai
from google.genai import types
# Import the theme injector
from chat_mode import inject_food_theme

st.set_page_config(page_title="Menu Analyzer", page_icon="📊")

# --- APPLY VISUAL THEME ---
inject_food_theme()

col1, col2 = st.columns([1, 2])
with col1:
    with st.container(border=True):
        st.page_link("main.py", label="**Back to Recipe Book**", icon="🏠", width="stretch")
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

# Create Plotly Bar Chart with THEMED COLORS
fig = go.Figure(data=[go.Bar(
    x=categories,
    y=counts,
    # Updated colors to match the Food/Spice Theme (Reds, Oranges, Warm tones)
    marker_color=['#E74C3C', '#C0392B', '#E67E22', '#F39C12', '#F5B041', '#D35400'] 
)])

fig.update_layout(
    title="Recipe Count by Main Ingredient",
    xaxis_title="Ingredient",
    yaxis_title="Number of Recipes",
    clickmode='event+select',
    # Update font in chart to match theme
    font=dict(family="Lato, sans-serif"),
    title_font=dict(family="Merriweather, serif")
)

selected_point = st.plotly_chart(fig, width="stretch", on_select="rerun")


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
    st.dataframe(df_result, width="stretch")
except Exception as e:
    st.error(f"Error fetching data: {e}")


# ==============================================================================
# CONTENT SECTION 3: Chat Interface (Conditional)
# ==============================================================================

if show_chat_section:
    st.divider()
    st.header("3. AI Menu Consultant 🤖")
    
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
        
        detail_query = 'SELECT "name(eng)", "condiments", "howto" FROM CSV_FILE WHERE "name(eng)" = ?'
        res = con.execute(detail_query, [selected_dish_menu]).fetchone()
        
        d_name = res[0] if res else ""
        d_ing = res[1] if res else ""
        d_how = res[2] if res else ""

        GEMINI_MODEL = "gemini-2.5-flash"
        
        try:
            if "geminiapi" in st.secrets.connections:
                client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
            else:
                st.error("Gemini API Key not found.")
                st.stop()
        except Exception as e:
            st.error(f"Error init Gemini: {e}")
            st.stop()

        system_instruction = f"""Context: You are a globally recognized expert Thai chef... (Instructions hidden for brevity - logic preserved) ..."""

        if 'chat_messages_menu' not in st.session_state:
            st.session_state.chat_messages_menu = [{"role": "model", "content": f"I see you are interested in **{d_name}**. How can I help you with this dish?"}]

        for msg in st.session_state.chat_messages_menu:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

        if prompt := st.chat_input(f"Ask about {d_name}..."):
            st.session_state.chat_messages_menu.append({'role': 'user', 'content': prompt})
            with st.chat_message('user'):
                st.write(prompt)

            with st.chat_message('model'):
                gemini_history = []
                for m in st.session_state.chat_messages_menu:
                    role = "user" if m["role"] == "user" else "model"
                    gemini_history.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
                
                try:
                    response_stream = client.models.generate_content_stream(
                        model=GEMINI_MODEL,
                        contents=gemini_history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    )
                    
                    def stream_parser(stream):
                        for chunk in stream:
                            if chunk.text:
                                yield chunk.text
                                
                    full_response = st.write_stream(stream_parser(response_stream))
                    st.session_state.chat_messages_menu.append({'role': 'model', 'content': full_response})
                    
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Please select a dish above to start the chat.")
