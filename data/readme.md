// 1. Create Person Nodes
LOAD CSV WITH HEADERS FROM 'https://raw.githubusercontent.com/ekaratnida/social-network/refs/heads/main/data/persons.csv' AS row
CREATE (:Person {id: toInteger(row.id), name: row.name, born: toInteger(row.born)});

// 2. Create Movie Nodes
LOAD CSV WITH HEADERS FROM 'https://raw.githubusercontent.com/ekaratnida/social-network/refs/heads/main/data/movies.csv' AS row
CREATE (:Movie {id: toInteger(row.id), title: row.title, released: toInteger(row.released), tagline: row.tagline});

// 3. Create Unique Constraints (Highly recommended for speed before matching relationships)
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE;

// 4. Create the ACTED_IN Relationships
LOAD CSV WITH HEADERS FROM 'https://raw.githubusercontent.com/ekaratnida/social-network/refs/heads/main/data/acted_in.csv' AS row
MATCH (p:Person {id: toInteger(row.person_id)})
MATCH (m:Movie {id: toInteger(row.movie_id)})
CREATE (p)-[:ACTED_IN {role: row.role}]->(m);

CALL gds.graph.project(
  'movieGraph',
  ['Person', 'Movie'],
  {
    ACTED_IN: {
      type: 'ACTED_IN',
      orientation: 'UNDIRECTED'
    }
  }
)
YIELD graphName, nodeCount, relationshipCount;

CALL gds.degree.stream('movieGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS Name, 
       gds.util.asNode(nodeId).title AS MovieTitle, 
       score AS Connections
ORDER BY Connections DESC;

CALL gds.beta.closeness.stream('movieGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS Name, 
       gds.util.asNode(nodeId).title AS MovieTitle, 
       score AS ClosenessScore
ORDER BY ClosenessScore DESC;

CALL gds.betweenness.stream('movieGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS Name, 
       gds.util.asNode(nodeId).title AS MovieTitle, 
       score AS BetweennessScore
ORDER BY BetweennessScore DESC;

CALL gds.graph.drop('movieGraph') YIELD graphName;
