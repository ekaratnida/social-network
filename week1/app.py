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

st.divider()
st.subheader("Manage People")

names_result = supabase.table("people").select("name").order("name").execute()
all_names = [r["name"] for r in names_result.data]

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Update Person**")
    if all_names:
        sel = st.selectbox("Select person", all_names, key="upd_person")
        ppl = supabase.table("people").select("*").eq("name", sel).execute()
        if ppl.data:
            p = ppl.data[0]
            new_hobby = st.text_input("Hobby", value=p.get("hobby") or "")
            new_age = st.number_input("Age", 1, 120, value=p.get("age") or 25)
            if st.button("Update Person"):
                supabase.table("people").update(
                    {"hobby": new_hobby, "age": new_age}
                ).eq("name", sel).execute()
                st.rerun()

with col2:
    st.markdown("**Delete Person**")
    if all_names:
        del_sel = st.selectbox("Select person", all_names, key="del_person")
        if st.button("Delete Person (and their edges)"):
            supabase.table("edges").delete().or_(
                f"person_a.eq.{del_sel},person_b.eq.{del_sel}"
            ).execute()
            supabase.table("people").delete().eq("name", del_sel).execute()
            st.rerun()

st.divider()
st.subheader("Manage Edges")

edges_result = supabase.table("edges").select("*").execute()
edge_list = edges_result.data

col3, col4 = st.columns(2)

with col3:
    st.markdown("**Update Edge**")
    if edge_list:
        edge_labels = [
            f"{e['person_a']} → {e['person_b']} ({e.get('relation') or 'no relation'})"
            for e in edge_list
        ]
        sel_edge_idx = st.selectbox("Select edge", range(len(edge_labels)), format_func=lambda i: edge_labels[i], key="upd_edge")
        sel_edge = edge_list[sel_edge_idx]
        new_rel = st.text_input("Relation", value=sel_edge.get("relation") or "")
        if st.button("Update Edge"):
            supabase.table("edges").update(
                {"relation": new_rel}
            ).eq("id", sel_edge["id"]).execute()
            st.rerun()

with col4:
    st.markdown("**Delete Edge**")
    if edge_list:
        del_edge_idx = st.selectbox("Select edge", range(len(edge_labels)), format_func=lambda i: edge_labels[i], key="del_edge")
        del_edge = edge_list[del_edge_idx]
        if st.button("Delete Edge"):
            supabase.table("edges").delete().eq("id", del_edge["id"]).execute()
            st.rerun()

with st.expander("People Data"):
    st.write(people)

with st.expander("Edge Data"):
    st.write(edges)
