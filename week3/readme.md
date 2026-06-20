# Lab
## 1) Run docker
```docker
docker run -d ^
  --name neo4j-gds ^
  -p 7474:7474 -p 7687:7687 ^
  -v neo4j_data:/data ^
  -v "%cd%\neo4j-import:/import" ^
  -e NEO4J_AUTH=neo4j/s3cureP@ssword ^
  -e NEO4J_PLUGINS="[\"graph-data-science\"]" ^
  -e NEO4J_dbms_security_procedures_unrestricted=gds.* ^
  --memory=2g ^
  neo4j:latest
```
## 2) Call website 
```
http://localhost:7474/
```

## 3) Type yr password: "s3cureP@ssword"
## 4) Put "users.csv" into the "neo4j-import" folder
## 5) Run the cypher command
```cypher
LOAD CSV WITH HEADERS FROM 'file:///users.csv' AS row
CREATE (p:Person {
  id: toInteger(row.id),
  name: row.name,
  role: row.role
});
```

## 6) Run the next cypher command
```cypher
MATCH (p:Person) RETURN p LIMIT 10;
```

## 7) Show GDS functions
```cypher
CALL gds.list();
```

## 8) Create a sample data
```cypher
CREATE (a:User {name: 'Alice'}), (b:User {name: 'Bob'}), (c:User {name: 'Charlie'}),
       (a)-[:LINKS]->(b), (b)-[:LINKS]->(c), (c)-[:LINKS]->(a);
```

## 9) Check the sample data
```cypher
MATCH (u:User)-[r:LINKS]->() RETURN u, r
```

## 10) Project the sample data to a memory
```cypher
CALL gds.graph.project('myGraph', 'User', 'LINKS');
```

## 11) Execute pagerank as an example
```cypher
CALL gds.pageRank.stream('myGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS name, score
ORDER BY score DESC;
```

## 12) Review centrality
12) centrality https://neo4j.com/docs/graph-data-science/current/algorithms/centrality/

## 13) Community detection
13) community https://neo4j.com/docs/graph-data-science/current/algorithms/community/

Necessary cmd
docker ps -a
docker rm -f container name
docker volume rm container name

