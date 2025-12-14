// Shortest prerequisite chain between two courses
MATCH
  (start:Course {code: $from}),
  (end:Course {code: $to})
CALL gds.shortestPath.dijkstra.stream(
  'courseGraph',
  {
    sourceNode: start,
    targetNode: end
  }
)
YIELD nodeIds
RETURN
  [nodeId IN nodeIds | gds.util.asNode(nodeId).code] AS path;

