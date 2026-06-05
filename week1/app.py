import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from supabase import create_client

st.set_page_config(page_title="Audience Network", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

def ensure_tables():
    try:
        supabase.table("people").select("*").limit(1).execute()
        supabase.table("favorites").select("*").limit(1).execute()
    except Exception:
        st.error(
            "Supabase tables not found."
            " Run the following SQL in your Supabase SQL Editor:\n\n"
            "```sql\n"
            "CREATE TABLE people (\n"
            "  id BIGSERIAL PRIMARY KEY,\n"
            "  name TEXT NOT NULL UNIQUE,\n"
            "  hobby TEXT,\n"
            "  age INTEGER\n"
            ");\n\n"
            "CREATE TABLE edges (\n"
            "  id BIGSERIAL PRIMARY KEY,\n"
            "  person_a TEXT NOT NULL,\n"
            "  person_b TEXT NOT NULL,\n"
            "  relation TEXT,\n"
            "  FOREIGN KEY (person_a) REFERENCES people(name),\n"
            "  FOREIGN KEY (person_b) REFERENCES people(name)\n"
            ");\n\n"
            "CREATE TABLE favorites (\n"
            "  id BIGSERIAL PRIMARY KEY,\n"
            "  person_name TEXT NOT NULL REFERENCES people(name),\n"
            "  food TEXT NOT NULL,\n"
            "  UNIQUE(person_name, food)\n"
            ");\n"
            "```"
        )
        st.stop()

@st.cache_data(ttl=10, show_spinner=False)
def fetch_people():
    return supabase.table("people").select("*").order("name").execute().data

@st.cache_data(ttl=10, show_spinner=False)
def fetch_edges():
    return supabase.table("edges").select("*").execute().data

@st.cache_data(ttl=10, show_spinner=False)
def fetch_favorites():
    return supabase.table("favorites").select("*").execute().data

@st.cache_data(ttl=10, show_spinner=False)
def fetch_names():
    data = supabase.table("people").select("name").order("name").execute().data
    return [r["name"] for r in data]

def mutate():
    st.cache_data.clear()
    st.rerun()

def add_audience_page():
    ensure_tables()
    st.title("Add Audience")

    col_left, col_right = st.columns([3, 1])
    with col_left:
        name = st.text_input("Name").strip()
    with col_right:
        st.markdown("###")
        if st.button("Clear All Data"):
            supabase.table("favorites").delete().neq("id", 0).execute()
            supabase.table("edges").delete().neq("id", 0).execute()
            supabase.table("people").delete().neq("id", 0).execute()
            mutate()

    if st.button("Add") and name:
        existing = supabase.table("people").select("name").eq("name", name).execute()
        if existing.data:
            st.error("Name already exists.")
        else:
            supabase.table("people").insert({"name": name}).execute()
            mutate()

    people = fetch_people()
    if people:
        st.subheader("Existing Audience")
        st.table([{"Name": p["name"]} for p in people])

FOODS = ["Chicken Rice", "Somtum", "Noodle", "Mooping"]

def network_page():
    ensure_tables()
    st.title("Network Visualizer")

    names = fetch_names()
    if names:
        sel = st.selectbox("Select person", names)
        favs = supabase.table("favorites").select("food").eq("person_name", sel).execute()
        current_foods = [r["food"] for r in favs.data]
        selected = st.multiselect("Favorite foods", FOODS, default=current_foods)
        if st.button("Save"):
            supabase.table("favorites").delete().eq("person_name", sel).execute()
            if selected:
                supabase.table("favorites").insert(
                    [{"person_name": sel, "food": f} for f in selected]
                ).execute()
            mutate()

    people = fetch_people()
    favorites = fetch_favorites()

    fav_map = {}
    for f in favorites:
        fav_map.setdefault(f["person_name"], set()).add(f["food"])

    if people:
        G = nx.Graph()
        for p in people:
            foods = ", ".join(sorted(fav_map.get(p["name"], set()))) or "none"
            G.add_node(p["name"], foods=foods)
        names_list = [p["name"] for p in people]
        for i in range(len(names_list)):
            for j in range(i + 1, len(names_list)):
                shared = fav_map.get(names_list[i], set()) & fav_map.get(names_list[j], set())
                if shared:
                    G.add_edge(names_list[i], names_list[j], shared=", ".join(sorted(shared)))

        fig, ax = plt.subplots(figsize=(10, 8))
        pos = nx.spring_layout(G, k=0.5, seed=42)
        nx.draw(G, pos, with_labels=True, node_color="skyblue",
                node_size=600, edge_color="gray", ax=ax)
        shared_labels = {(u, v): d["shared"] for u, v, d in G.edges(data=True)}
        if shared_labels:
            nx.draw_networkx_edge_labels(G, pos, edge_labels=shared_labels, ax=ax)
        ax.axis("off")
        st.pyplot(fig)

    with st.expander("Favorite Foods Data"):
        st.write(favorites)

pg = st.navigation([
    st.Page(add_audience_page, title="Add Audience"),
    st.Page(network_page, title="Network Visualizer"),
])
pg.run()
