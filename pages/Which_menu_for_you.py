import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
from google import genai
from google.genai import types
import pandas as pd

st.set_page_config(page_title="Menu Analyzer", page_icon="📊")

col1, col2 = st.columns([1, 2])
with col1:
    with st.container(border=True):
        st.page_link("main.py", label="**Back to Recipe Book**", icon="🏠",use_container_width=True)
st.divider()
# --- 1. SETUP DATABASE CONNECTION (Copied from existing logic) ---
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

st.title("📊 Ingredient Analyzer")

# --- 2. SIDEBAR SETUP ---
st.sidebar.title("AI Chef Mode 🤖")
# Toggle to show/hide Section 3 (Chat)
show_chat_section = st.sidebar.toggle("Enable AI Chat Assistant", value=False)


# ==============================================================================
# CONTENT SECTION 1: Condiments Bar Plot
# ==============================================================================
st.subheader("1. Ingredient Distribution")

# Define categories
categories = ['Pork', 'Beef', 'Prawn', 'Chicken', 'Fish','Other']
counts = []

# Calculate counts using SQL queries on the DuckDB connection
for cat in categories:
    if cat == 'Fish':
        # Specific logic for fish including snakehead or mackerel
        query = f"""
            SELECT count(*) FROM CSV_FILE 
            WHERE "condiments" ILIKE '%mackerel%' 
            OR "condiments" ILIKE '%snakehead%' 
        """
    elif cat == 'Other':
        query = f"""
            SELECT count(*) FROM CSV_FILE
            WHERE "condiments" NOT ILIKE '%mackerel%'
            AND "condiments" NOT ILIKE '%snakehead%'
            AND "condiments" NOT ILIKE '%pork%'
            AND "condiments" NOT ILIKE '%beef%'
            AND "condiments" NOT ILIKE '%prawn%'
            AND "condiments" NOT ILIKE '%chicken%';
        """
    elif cat == 'Pork':
        query = f"""
            SELECT count(*) FROM CSV_FILE
            WHERE "condiments" ILIKE '%pork%'
            AND (
                    "condiments" NOT ILIKE '%mackerel%' AND
                    "condiments" NOT ILIKE '%snakehead%' AND
                    "condiments" NOT ILIKE '%beef%' AND
                    "condiments" NOT ILIKE '%chicken%'
                );
        """
    else:
        query = f"""
            SELECT count(*) FROM CSV_FILE 
            WHERE "condiments" ILIKE '%{cat}%'
        """
    
    result = con.execute(query).fetchone()
    counts.append(result[0] if result else 0)

# Create Plotly Bar Chart
fig = go.Figure(data=[go.Bar(
    x=categories,
    y=counts,
    marker_color=['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#D9B3FF',"#FDFEA0"] # Just some pastel colors
)])

fig.update_layout(
    title="Recipe Count by Main Ingredient",
    xaxis_title="Ingredient",
    yaxis_title="Number of Recipes",
    clickmode='event+select'
)

# Render the chart with selection enabled
# The 'on_select="rerun"' allows us to detect clicks and update the table below
selected_point = st.plotly_chart(fig, width="stretch", on_select="rerun")


# ==============================================================================
# CONTENT SECTION 2: Query Table
# ==============================================================================
st.subheader("2. Filtered Recipe List")

# Determine which category is selected. Default to showing all if nothing selected.
selected_category = None

# Logic to extract the category from the Plotly selection event
if selected_point and selected_point['selection']['points']:
    # Get the x-value (category name) of the clicked bar
    selected_category = selected_point['selection']['points'][0]['x']

# Build the Query for the Table
if selected_category:
    st.info(f"Showing recipes containing: **{selected_category.capitalize()}**")
    if selected_category == 'Fish':
        table_query = """
            SELECT "name(eng)" AS Menu 
            FROM CSV_FILE 
            WHERE "condiments" ILIKE '%mackerel%' 
            OR "condiments" ILIKE '%snakehead%' 
        """
    elif selected_category == 'Other':
        table_query = f"""
            SELECT "name(eng)" AS Menu
            FROM CSV_FILE
            WHERE "condiments" NOT ILIKE '%mackerel%'
            AND "condiments" NOT ILIKE '%snakehead%'
            AND "condiments" NOT ILIKE '%pork%'
            AND "condiments" NOT ILIKE '%beef%'
            AND "condiments" NOT ILIKE '%prawn%'
            AND "condiments" NOT ILIKE '%chicken%';
        """
    elif selected_category == 'Pork':
        table_query = f"""
            SELECT "name(eng)" AS Menu
            FROM CSV_FILE
            WHERE "condiments" ILIKE '%pork%'
            AND (
                    "condiments" NOT ILIKE '%mackerel%' AND
                    "condiments" NOT ILIKE '%snakehead%' AND
                    "condiments" NOT ILIKE '%beef%' AND
                    "condiments" NOT ILIKE '%chicken%'
                );
        """
    else:
        table_query = f"""
            SELECT "name(eng)" AS Menu
            FROM CSV_FILE 
            WHERE "condiments" ILIKE '%{selected_category}%'
        """
else:
    st.write("Displaying all recipes containing the analyzed ingredients (Click a bar above to filter).")
    # Query to show all rows that match ANY of the categories
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
    
    # --- Dish Selector ---
    # We need to fetch the titles list again since we can't import it from main.py directly
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

    # --- Chat Logic (Only active if a dish is selected) ---
    if selected_dish_menu:
        
        # Fetch details for the context
        detail_query = 'SELECT "name(eng)", "condiments", "howto" FROM CSV_FILE WHERE "name(eng)" = ?'
        res = con.execute(detail_query, [selected_dish_menu]).fetchone()
        
        d_name = res[0] if res else ""
        d_ing = res[1] if res else ""
        d_how = res[2] if res else ""

        # Chat Configuration
        GEMINI_MODEL = "gemini-2.5-flash"
        
        # Initialize Client
        try:
            if "geminiapi" in st.secrets.connections:
                client = genai.Client(api_key=st.secrets.connections.geminiapi["GEMINI_API_KEY"])
            else:
                st.error("Gemini API Key not found.")
                st.stop()
        except Exception as e:
            st.error(f"Error init Gemini: {e}")
            st.stop()

        # System Instruction
        system_instruction = f"""Context: You are a globally recognized expert Thai chef, specializing in adapting and translating authentic Thai recipes for cooks in other countries. Your primary expertise lies in **substituting hard-to-find ingredients** with readily available international alternatives while preserving the integrity of the dish’s flavor profile (taste, aroma, and texture)."
    Task: Guide the user through the process of preparing and cooking the specified recipe. Provide detailed, insightful culinary advice, and respond comprehensively to all user questions regarding ingredients, techniques, and potential substitutions. You must act as a patient, encouraging, and highly knowledgeable mentor.,
            
    Recipe_Data:
                Name: **{d_name}**
                Ingredients: **{d_ing}**
                Instructions: **{d_how}**
    Guidelines: **Substitution Protocol:** When a user asks for a substitution, or when you proactively suggest one, you must explicitly state the original, authentic Thai ingredient and its recommended substitute, followed by a brief, specific explanation of *why* the substitute works (e.g., 'substituting palm sugar with brown sugar for its molasses notes and soft texture').,
                **Accuracy and Flavor Integrity:** Only propose substitutions that maintain the essential balance (spicy, sour, sweet, salty) and core character of the Thai dish. If a perfect substitution is impossible, explain the compromise or nearest achievable flavor profile.,
                **Instruction Modification:** If an ingredient substitution necessitates a change to the original cooking instructions (e.g., a change in cooking time or technique), you must detail the revised instruction step clearly to ensure the ‘better version’ of the dish is achieved.,
                **Technique Explanations:** When discussing cooking techniques, use specific, detailed language (e.g., temperature control, oil choice, wok movement) to enhance the user’s understanding.
    Constraints: Maintain the expert Thai chef persona at all times.,
                All responses must be written in English (United Kingdom).,
                Do not fabricate culinary facts, ingredient interactions, or nonexistent techniques (avoiding hallucinations). If you lack sufficient information, state what additional detail is needed.,
                The initial guidance provided must be based specifically on the Recipe_Data provided above, but can be substituted if the recipe does not make sense or is not up to Thai standard.
    """

        # Session State for this specific page's chat
        if 'chat_messages_menu' not in st.session_state:
            st.session_state.chat_messages_menu = [{"role": "model", "content": f"I see you are interested in **{d_name}**. How can I help you with this dish?"}]

        # Display History
        for msg in st.session_state.chat_messages_menu:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

        # Chat Input
        if prompt := st.chat_input(f"Ask about {d_name}..."):
            # User Msg
            st.session_state.chat_messages_menu.append({'role': 'user', 'content': prompt})
            with st.chat_message('user'):
                st.write(prompt)

            # Model Msg
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
