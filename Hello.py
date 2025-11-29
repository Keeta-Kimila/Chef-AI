import streamlit as st
import duckdb
from streamlit_gsheets import GSheetsConnection

@st.cache_data
def load_datafood(name):
    mycon = st.connection(name, type=GSheetsConnection)
    df = mycon.read(usecols=[1,2,3])
    return df
CSV_FILE = load_datafood("datafoods")
con = duckdb.connect(database=':memory:')



st.set_page_config(
    page_title="Best Thai Recipe",
    page_icon="👋",
)

st.write("# Best Thai recipe with any ingredients! 👋")
st.sidebar.title("Recipe Book 📖")
st.sidebar.write("Select a dish below:")


st.markdown(
    """
    Our website allows anyone from any part of the world to be able to make Thai cuisine
    , with our AI helper, any ingredients that are Thai but are unable to be found in your countries
    can be substituted with the help of our AI chef guidance!
    **Select the recipe from our sidebar menu** to get started!
    ### Or have your own recipe from a Youtube video and have no ingredients?
    - Paste the video link to our AI and ask away! [streamlit.io](link)
"""
)

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
    
    if result:
        dish_name = result[0]
        dish_ingredients = result[1]
        dish_instructions = result[2]

        # --- Display Title ---
        st.header(dish_name)

        # --- Display Ingredients ---
        st.subheader("🛒 Ingredients")
        # Your CSV uses newlines to separate ingredients, so we split by \n
        if dish_ingredients:
            for line in dish_ingredients.split('\n'):
                line = line.strip()
                if line:  # Only display non-empty lines
                    st.write(f"- {line}")
        else:
            st.info("No ingredients listed.")

        # --- Display Instructions ---
        st.subheader("👨‍🍳 How to make")
        # Note: The 'howto' column in your current CSV seems to be in Thai.
        if dish_instructions:
            st.write(dish_instructions)
        else:
            st.info("No instructions available.")
