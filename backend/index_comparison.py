"""
索引比较API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel

from services.index_comparison_service import IndexComparisonService
from services.vector_store_service import VectorStoreService

router = APIRouter(prefix="/api/index-comparison", tags=["index-comparison"])

class IndexConfig(BaseModel):
    type: str
    params: Optional[Dict] = {}

class ComparisonRequest(BaseModel):
    index_configs: List[IndexConfig]
    test_queries: Optional[List[str]] = None
    k_values: Optional[List[int]] = [5, 10, 20, 50]

# 初始化服务
index_comparison_service = IndexComparisonService()
vector_store_service = VectorStoreService()

@router.post("/build")
async def build_indexes(request: ComparisonRequest, background_tasks: BackgroundTasks):
    """构建多种索引用于比较"""
    try:
        # 获取现有向量数据
        vectors_data = await vector_store_service.get_all_vectors()
        if not vectors_data:
            raise HTTPException(status_code=404, detail="No vectors found in database")
        
        vectors = [np.array(v['vector']) for v in vectors_data]
        ids = [v['id'] for v in vectors_data]
        
        configs = [
            {"type": cfg.type, "params": cfg.params or {}}
            for cfg in request.index_configs
        ]
        
        # 在后台构建索引（避免阻塞）
        background_tasks.add_task(
            index_comparison_service.build_multiple_indexes,
            vectors, ids, configs
        )
        
        return {
            "message": "Index building started",
            "configs": request.index_configs,
            "vector_count": len(vectors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
async def compare_indexes(request: ComparisonRequest):
    """比较不同索引的性能"""
    try:
        # 准备测试查询向量
        test_queries = request.test_queries or ["示例查询1", "示例查询2"]
        query_vectors = []
        
        for query in test_queries:
            vector = await vector_store_service.embedding_service.embed_text(query)
            query_vectors.append(np.array(vector))
        
        # 执行性能比较
        performance_df = index_comparison_service.compare_performance(
            query_vectors, 
            request.k_values
        )
        
        # 获取比较报告
        report = index_comparison_service.get_comparison_report()
        
        return {
            "performance_metrics": performance_df.to_dict(orient="records"),
            "report": report,
            "test_queries": test_queries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis")
async def get_index_analysis():
    """获取索引分析报告"""
    try:
        report = index_comparison_service.get_comparison_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommend")
async def get_recommendation(vector_count: int, dimension: int, 
                            query_per_second: int = 100,
                            memory_limit_mb: int = 1024):
    """根据场景推荐最佳索引"""
    recommendations = []
    
    if vector_count < 10000:
        recommendations.append({
            "index_type": "flat",
            "reason": "数据量小，FLAT索引可提供100%召回率且实现简单",
            "expected_performance": "查询延迟<10ms"
        })
    elif vector_count < 100000:
        recommendations.append({
            "index_type": "ivf_flat",
            "reason": "中等数据量，IVF_FLAT提供速度和召回率的平衡",
            "params": {"nlist": min(vector_count // 10, 100)},
            "expected_performance": "查询延迟<50ms, 召回率>95%"
        })
        recommendations.append({
            "index_type": "annoy",
            "reason": "内存敏感场景，Annoy索引占用内存小",
            "params": {"n_trees": 10},
            "expected_performance": "查询延迟<30ms, 内存占用~200MB"
        })
    else:
        recommendations.append({
            "index_type": "hnsw",
            "reason": "大规模数据且要求高召回率",
            "params": {"M": 16, "ef_construction": 200},
            "expected_performance": "查询延迟<100ms, 召回率>99%"
        })
        recommendations.append({
            "index_type": "ivf_sq8",
            "reason": "超大规模且内存受限，量化压缩存储",
            "expected_performance": "内存减少75%, 召回率~90%"
        })
    
    return {
        "vector_count": vector_count,
        "dimension": dimension,
        "query_per_second": query_per_second,
        "memory_limit_mb": memory_limit_mb,
        "recommendations": recommendations
    }