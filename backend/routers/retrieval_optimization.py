"""
检索优化API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from services.retrieval_optimization_service import RetrievalOptimizationService
from services.search_service import SearchService

router = APIRouter(prefix="/api/retrieval-optimization", tags=["retrieval-optimization"])

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    enable_pre_optimization: bool = True
    enable_post_optimization: bool = True

class OptimizationResponse(BaseModel):
    original_query: str
    pre_optimization: Optional[Dict] = None
    retrieval_results: Optional[List[Dict]] = None
    post_optimization: Optional[Dict] = None
    final_results: List[Dict]

# 初始化服务
retrieval_opt_service = RetrievalOptimizationService()
search_service = SearchService()

@router.post
