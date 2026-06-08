import json
import streamlit as st
import networkx as nx
from supabase import create_client

st.set_page_config(page_title="User Network", layout="wide")

st.markdown("""
<style>
table { border-collapse: collapse; }
td, th { border: 1px solid #ddd !important; padding: 8px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("### DADS Survey")
st.sidebar.markdown("[dads-survey.streamlit.app](https://dads-survey.streamlit.app/)")

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
            "  name TEXT NOT NULL UNIQUE\n"
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

FOODS = ["Chicken Rice", "Somtum", "Noodle", "Mooping", "Pizza"]

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
    st.markdown("# Social Network and Media Analysis")
    st.title("Add User Name")

    col_left, col_right = st.columns([3, 1])
    with col_left:
        name = st.text_input("Name").strip()
    with col_right:
        if st.session_state.get("current_user") == "Ekarat":
            st.markdown("###")
            if st.button("Clear All Data"):
                supabase.table("favorites").delete().neq("id", 0).execute()
                supabase.table("edges").delete().neq("id", 0).execute()
                supabase.table("people").delete().neq("id", 0).execute()
                st.session_state.pop("current_user", None)
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
        st.subheader("Existing Users")
        st.table([{"Name": p["name"]} for p in people])

        st.divider()
        sel = st.selectbox("Select a user to set preferences", [p["name"] for p in people])
        if st.button("Confirm User"):
            st.session_state.current_user = sel
            st.success(f"Selected: {sel}. Go to Preferences page.")

def preferences_page():
    ensure_tables()
    st.title("Preferences")

    if "current_user" not in st.session_state:
        st.warning("No user selected. Go to Add User Name page and select a user first.")
        return

    user = st.session_state.current_user

    favs = supabase.table("favorites").select("food").eq("person_name", user).execute()
    current_foods = [r["food"] for r in favs.data]

    known = supabase.table("edges").select("person_b").eq("person_a", user).eq("relation", "knows").execute()
    current_known = [r["person_b"] for r in known.data]

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown(f"**{user}**")
    with r1c2:
        st.markdown("**likes**")
    with r1c3:
        idx = FOODS.index(current_foods[0]) if current_foods else None
        selected_food = st.radio("", FOODS, index=idx)

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.markdown(f"**{user}**")
    with r2c2:
        st.markdown("**knows**")
    with r2c3:
        other_names = [n for n in fetch_names() if n != user]
        selected_known = st.multiselect("", other_names, default=current_known)

    if st.button("Save"):
        supabase.table("favorites").delete().eq("person_name", user).execute()
        if selected_food:
            supabase.table("favorites").insert(
                {"person_name": user, "food": selected_food}
            ).execute()

        supabase.table("edges").delete().eq("person_a", user).eq("relation", "knows").execute()
        if selected_known:
            supabase.table("edges").insert(
                [{"person_a": user, "person_b": p, "relation": "knows"} for p in selected_known]
            ).execute()
        mutate()

def network_page():
    ensure_tables()
    st.title("Network Visualizer")

    people = fetch_people()
    favorites = fetch_favorites()
    edges = fetch_edges()

    if not people:
        st.info("No users yet.")
        return

    G = nx.Graph()
    for name in fetch_names():
        G.add_node(name, kind="person")
    for food in FOODS:
        G.add_node(food, kind="food")
    for f in favorites:
        G.add_edge(f["person_name"], f["food"], label="likes")
    for e in edges:
        G.add_edge(e["person_a"], e["person_b"], label=e["relation"])

    vis_nodes = []
    vis_edges = []
    for n, d in G.nodes(data=True):
        kind = d.get("kind", "person")
        vis_nodes.append({
            "id": n,
            "label": n,
            "color": {"background": "skyblue", "border": "navy"} if kind == "person"
                      else {"background": "lightgreen", "border": "darkgreen"},
            "shape": "dot",
            "size": 30 if kind == "person" else 20,
            "font": {"size": 16, "color": "#111", "bold": True, "face": "Arial"},
        })
    for u, v, d in G.edges(data=True):
        vis_edges.append({
            "from": u,
            "to": v,
            "label": d.get("label", ""),
            "color": "gray",
            "width": 2,
            "font": {"size": 13, "color": "#222", "strokeWidth": 3, "strokeColor": "white", "bold": True},
            "smooth": {"type": "curvedCW", "roundness": 0.1},
        })

    html = f"""
    <html>
    <head>
      <script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
      <style>
        body {{ margin: 0; overflow: hidden; }}
        #network {{ width: 100vw; height: 100vh; background-color: #FFFF00; }}
      </style>
    </head>
    <body>
      <div id="network"></div>
      <script>
        var nodes = new vis.DataSet({json.dumps(vis_nodes)});
        var edges = new vis.DataSet({json.dumps(vis_edges)});
        var container = document.getElementById('network');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
          physics: {{ solver: 'forceAtlas2Based', stabilization: {{ iterations: 100 }} }},
          interaction: {{ dragNodes: true, dragView: true, zoomView: true, hover: true }},
          edges: {{ smooth: {{ type: 'curvedCW', roundness: 0.1 }} }},
          height: '100%',
          backgroundColor: { background: '#FFFF00' },
        }};
        var network = new vis.Network(container, data, options);
      </script>
    </body>
    </html>
    """
    st.components.v1.html(html, height=700)

    with st.expander("Raw Data"):
        st.write("People", people)
        st.write("Favorites", favorites)
        st.write("Edges", edges)

pg = st.navigation([
    st.Page(add_audience_page, title="1. Add User Name"),
    st.Page(preferences_page, title="2. Preferences"),
    st.Page(network_page, title="3. Network Visualizer"),
])
pg.run()
