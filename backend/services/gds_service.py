from backend.database.neo4j import get_neo4j_client


def get_pagerank(limit: int = 10):
    """
    Run PageRank on the projected course graph and return top courses.
    """
    client = get_neo4j_client()

    query = """
    CALL gds.pageRank.stream('courseGraph')
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).code AS course, score
    ORDER BY score DESC
    LIMIT $limit
    """

    result = client.query(query, {"limit": limit})
    return [{"course": r["course"], "score": r["score"]} for r in result]

