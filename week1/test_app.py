import json
import pytest
import networkx as nx


FOODS = ["Chicken Rice", "Somtum", "Noodle", "Mooping", "Pizza"]


def build_graph(people, favorites, edges):
    G = nx.Graph()
    for name in people:
        G.add_node(name, kind="person")
    for food in FOODS:
        G.add_node(food, kind="food")
    for f in favorites:
        G.add_edge(f["person_name"], f["food"], label="likes")
    for e in edges:
        G.add_edge(e["person_a"], e["person_b"], label=e["relation"])
    return G


def build_vis_nodes(G, cent, highlight_nodes, scale=250):
    pos = nx.spring_layout(G, k=2.5, seed=42)
    is_basic = not bool(cent)
    vis_nodes = []
    for n, d in G.nodes(data=True):
        kind = d.get("kind", "person")
        has_cent = not is_basic
        is_highlighted = n in highlight_nodes
        score = cent.get(n, 0) if has_cent else None
        label = f"{n}\n{score:.3f}" if score is not None else n
        bg = "skyblue" if kind == "person" else "lightgreen"
        border = "red" if is_highlighted else ("navy" if kind == "person" else "darkgreen")
        node = {
            "id": n,
            "label": label,
            "color": {"background": bg, "border": border},
            "shape": "ellipse",
            "x": pos[n][0] * scale,
            "y": pos[n][1] * scale,
            "size": 30 if kind == "person" else 20,
            "font": {"size": 13, "color": "#111", "bold": True, "face": "Arial", "align": "center"},
            "opacity": 1.0 if not has_cent or is_highlighted else 0.2,
        }
        if is_highlighted:
            node["borderWidth"] = 4
            node["size"] += 10
        vis_nodes.append(node)
    return vis_nodes


def build_vis_edges(G):
    vis_edges = []
    for u, v, d in G.edges(data=True):
        vis_edges.append({
            "from": u,
            "to": v,
            "label": d.get("label", ""),
            "color": "gray",
            "width": 2,
            "font": {"size": 13, "color": "#222", "strokeWidth": 3, "strokeColor": "white", "bold": True},
            "smooth": False,
        })
    return vis_edges


class TestBuildGraph:
    def test_empty_graph(self):
        G = build_graph([], [], [])
        assert G.number_of_nodes() == len(FOODS)
        assert G.number_of_edges() == 0

    def test_people_and_foods(self):
        G = build_graph(["Alice"], [], [])
        assert G.has_node("Alice")
        assert G.nodes["Alice"]["kind"] == "person"
        for f in FOODS:
            assert G.has_node(f)
            assert G.nodes[f]["kind"] == "food"

    def test_likes_edges(self):
        G = build_graph(["Alice"], [{"person_name": "Alice", "food": "Pizza"}], [])
        assert G.has_edge("Alice", "Pizza")
        assert G.edges["Alice", "Pizza"]["label"] == "likes"

    def test_knows_edges(self):
        G = build_graph(["Alice", "Bob"], [], [{"person_a": "Alice", "person_b": "Bob", "relation": "knows"}])
        assert G.has_edge("Alice", "Bob")
        assert G.edges["Alice", "Bob"]["label"] == "knows"


class TestVisNodes:
    def test_basic_stats_no_cent(self):
        G = build_graph(["Alice", "Bob"], [{"person_name": "Alice", "food": "Pizza"}], [])
        nodes = build_vis_nodes(G, {}, [])
        assert len(nodes) == G.number_of_nodes()
        for n in nodes:
            assert n["opacity"] == 1.0
            assert n["label"] == n["id"]

    def test_degree_cent_labels(self):
        G = build_graph(["Alice"], [{"person_name": "Alice", "food": "Pizza"}], [])
        cent = nx.degree_centrality(G)
        top5 = sorted(cent, key=cent.get, reverse=True)[:5]
        nodes = build_vis_nodes(G, cent, top5)
        alice = next(n for n in nodes if n["id"] == "Alice")
        assert "\n" in alice["label"]
        score = float(alice["label"].split("\n")[1])
        assert 0 < score <= 1

    def test_highlighted_nodes(self):
        G = build_graph(["Alice", "Bob"], [{"person_name": "Alice", "food": "Pizza"}, {"person_name": "Bob", "food": "Pizza"}], [])
        cent = nx.degree_centrality(G)
        top5 = sorted(cent, key=cent.get, reverse=True)[:5]
        nodes = build_vis_nodes(G, cent, top5)
        for n in nodes:
            if n["id"] in top5:
                assert n["borderWidth"] == 4
                assert n["color"]["border"] == "red"
            else:
                assert n["opacity"] == 0.2

    def test_faded_non_highlighted(self):
        G = build_graph(["Alice", "Bob", "Charlie"], [
            {"person_name": "Alice", "food": "Pizza"},
            {"person_name": "Bob", "food": "Noodle"},
        ], [])
        cent = nx.degree_centrality(G)
        top5 = sorted(cent, key=cent.get, reverse=True)[:5]
        nodes = build_vis_nodes(G, cent, top5)
        highlighted = {n["id"] for n in nodes if n.get("borderWidth") == 4}
        for n in nodes:
            if n["id"] in highlighted:
                assert n["opacity"] == 1.0
            else:
                assert n["opacity"] == 0.2


class TestVisEdges:
    def test_edge_labels(self):
        G = build_graph(["Alice"], [{"person_name": "Alice", "food": "Pizza"}],
                        [{"person_a": "Alice", "person_b": "Bob", "relation": "knows"}])
        edges = build_vis_edges(G)
        labels = {e["label"] for e in edges}
        assert "likes" in labels
        assert "knows" in labels


class TestCentralityTable:
    def test_all_centralities_computed(self):
        people = ["Alice", "Bob"]
        favorites = [{"person_name": "Alice", "food": "Pizza"}]
        edges_data = [{"person_a": "Alice", "person_b": "Bob", "relation": "knows"}]
        G = build_graph(people, favorites, edges_data)
        deg = nx.degree_centrality(G)
        clo = nx.closeness_centrality(G)
        bet = nx.betweenness_centrality(G)
        eig = nx.eigenvector_centrality(G, max_iter=1000)
        kat = nx.katz_centrality(G, alpha=0.1, beta=1.0)
        for n in G.nodes():
            assert n in deg
            assert n in clo
            assert n in bet
            assert n in eig
            assert n in kat

    def test_centrality_values_in_range(self):
        G = build_graph(["Alice", "Bob"], [{"person_name": "Alice", "food": "Somtum"}], [])
        deg = nx.degree_centrality(G)
        for v in deg.values():
            assert 0 <= v <= 1
