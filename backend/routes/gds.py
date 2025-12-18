from fastapi import APIRouter
from backend.services import gds_service

router = APIRouter(prefix="/gds", tags=["Graph Data Science"])


@router.get("/pagerank")
def pagerank(limit: int = 10):
    """
    Return the most important courses using PageRank.
    """
    return {
        "algorithm": "PageRank",
        "limit": limit,
        "results": gds_service.get_pagerank(limit)
    }

