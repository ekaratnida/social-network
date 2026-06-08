import streamlit as st
import networkx as nx
import plotly.graph_objects as go
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

    fav_map = {}
    for f in favorites:
        fav_map.setdefault(f["person_name"], set()).add(f["food"])

    G = nx.Graph()
    for name in fetch_names():
        G.add_node(name, kind="person")
    for food in FOODS:
        G.add_node(food, kind="food")
    for f in favorites:
        G.add_edge(f["person_name"], f["food"], label="likes")
    for e in edges:
        G.add_edge(e["person_a"], e["person_b"], label=e["relation"])

    pos = nx.spring_layout(G, k=0.5, seed=42)
    pos_x = {n: p[0] for n, p in pos.items()}
    pos_y = {n: p[1] for n, p in pos.items()}

    person_nodes = [n for n, d in G.nodes(data=True) if d.get("kind") == "person"]
    food_nodes = [n for n, d in G.nodes(data=True) if d.get("kind") == "food"]

    edge_traces = []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos_x[u], pos_y[u]
        x1, y1 = pos_x[v], pos_y[v]
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(color="gray", width=1.5),
            hoverinfo="none",
            showlegend=False,
        ))

    person_trace = go.Scatter(
        x=[pos_x[n] for n in person_nodes],
        y=[pos_y[n] for n in person_nodes],
        mode="markers+text",
        text=person_nodes,
        textposition="top center",
        marker=dict(size=18, color="skyblue", line=dict(color="navy", width=2)),
        name="Person",
    )

    food_trace = go.Scatter(
        x=[pos_x[n] for n in food_nodes],
        y=[pos_y[n] for n in food_nodes],
        mode="markers+text",
        text=food_nodes,
        textposition="top center",
        marker=dict(size=14, color="lightgreen", line=dict(color="darkgreen", width=2)),
        name="Food",
    )

    edge_label_annotations = []
    for u, v, d in G.edges(data=True):
        edge_label_annotations.append(dict(
            x=(pos_x[u] + pos_x[v]) / 2,
            y=(pos_y[u] + pos_y[v]) / 2,
            text=d["label"],
            showarrow=False,
            font=dict(size=11, color="#444"),
            bgcolor="rgba(255,255,255,0.7)",
        ))

    fig = go.Figure(data=edge_traces + [person_trace, food_trace])
    fig.update_layout(
        title="Network Graph",
        title_x=0.5,
        showlegend=True,
        hovermode="closest",
        width=1000,
        height=700,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        plot_bgcolor="white",
        annotations=edge_label_annotations,
    )
    st.plotly_chart(fig, use_container_width=True)

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
