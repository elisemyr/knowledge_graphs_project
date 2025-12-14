// PageRank: identify structurally important courses
CALL gds.pageRank.stream('courseGraph')
YIELD nodeId, score
RETURN
  gds.util.asNode(nodeId).code AS course,
  score
ORDER BY score DESC
LIMIT 10;

