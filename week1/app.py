import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from supabase import create_client

st.set_page_config(page_title="Audience Network", layout="wide")
st.title("Audience Network Visualizer")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

def ensure_tables():
    try:
        supabase.table("people").select("*").limit(1).execute()
    except Exception:
        st.error(
            "Supabase tables not found. "
            "Run the following SQL in your Supabase SQL Editor:\n\n"
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
            ");\n"
            "```"
        )
        st.stop()

ensure_tables()

with st.form("add_person"):
    name = st.text_input("Name").strip()
    hobby = st.text_input("Hobby")
    age = st.number_input("Age", 1, 120, 25)
    if st.form_submit_button("Add") and name:
        existing = supabase.table("people").select("name").eq("name", name).execute()
        if existing.data:
            st.error("Name already exists.")
        else:
            supabase.table("people").insert(
                {"name": name, "hobby": hobby, "age": age}
            ).execute()
            st.rerun()

with st.form("add_edge"):
    names_result = supabase.table("people").select("name").order("name").execute()
    names = [r["name"] for r in names_result.data]
    if names:
        a, b = st.selectbox("Person A", names), st.selectbox("Person B", names)
        rel = st.text_input("Relation (e.g. friend)")
        if st.form_submit_button("Connect") and a != b:
            supabase.table("edges").insert(
                {"person_a": a, "person_b": b, "relation": rel}
            ).execute()
            st.rerun()

people_result = supabase.table("people").select("*").execute()
edges_result = supabase.table("edges").select("*").execute()
people = people_result.data
edges = edges_result.data

if people:
    G = nx.Graph()
    for p in people:
        G.add_node(p["name"], hobby=p.get("hobby"), age=p.get("age"))
    for e in edges:
        G.add_edge(e["person_a"], e["person_b"], relation=e.get("relation"))

    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(G, k=0.5, seed=42)
    nx.draw(G, pos, with_labels=True, node_color="skyblue",
            node_size=600, edge_color="gray", ax=ax)
    nx.draw_networkx_edge_labels(G, pos,
        edge_labels={(u, v): d["relation"] for u, v, d in G.edges(data=True)}, ax=ax)
    ax.axis("off")
    st.pyplot(fig)

with st.expander("People Data"):
    st.write(people)

with st.expander("Edge Data"):
    st.write(edges)
