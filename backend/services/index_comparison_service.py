"""
向量索引比较分析服务
"""
import time
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from utils.index_factory import IndexFactory, IndexType, VectorIndex

class IndexComparisonService:
    """索引比较分析服务"""
    
    def __init__(self):
        self.indexes: Dict[str, VectorIndex] = {}
        self.comparison_results: Dict[str, Any] = {}
        
    def build_multiple_indexes(self, 
                               vectors: List[np.ndarray], 
                               ids: List[str],
                               configs: List[Dict]) -> Dict[str, Any]:
        """
        构建多种索引类型
        configs: [
            {"type": "flat"},
            {"type": "ivf_flat", "params": {"nlist": 50}},
            {"type": "hnsw", "params": {"M": 16, "ef_construction": 200}},
            {"type": "annoy", "params": {"n_trees": 10}}
        ]
        """
        results = {}
        dimension = len(vectors[0]) if vectors else 0
        
        for config in configs:
            index_type_str = config.get("type", "flat")
            params = config.get("params", {})
            
            try:
                index_type = IndexType(index_type_str)
                start_time = time.time()
                
                # 创建并构建索引
                index = IndexFactory.create_index(index_type, dimension, **params)
                index.add_vectors(vectors, ids)
                
                build_time = time.time() - start_time
                
                results[index_type_str] = {
                    "index": index,
                    "build_time": build_time,
                    "memory_usage": self._estimate_memory_usage(index),
                    "params": params
                }
                
            except Exception as e:
                print(f"Failed to build {index_type_str} index: {e}")
                results[index_type_str] = {"error": str(e)}
                
        self.indexes = {k: v["index"] for k, v in results.items() if "index" in v}
        return results
    
    def compare_performance(self, 
                           query_vectors: List[np.ndarray],
                           k_values: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
        """比较不同索引的检索性能"""
        results = []
        
        for index_name, index in self.indexes.items():
            for k in k_values:
                # 测试查询性能
                query_times = []
                accuracies = []
                
                for query in query_vectors:
                    start_time = time.time()
                    search_results = index.search(query, k)
                    query_time = time.time() - start_time
                    query_times.append(query_time)
                    
                    # 计算召回率（以FLAT索引结果为基准）
                    if "flat" in self.indexes and index_name != "flat":
                        flat_results = self.indexes["flat"].search(query, k)
                        accuracy = self._calculate_recall(search_results, flat_results)
                        accuracies.append(accuracy)
                
                results.append({
                    "index_type": index_name,
                    "k": k,
                    "avg_query_time_ms": np.mean(query_times) * 1000,
                    "std_query_time_ms": np.std(query_times) * 1000,
                    "avg_recall": np.mean(accuracies) if accuracies else 1.0,
                    "p95_query_time_ms": np.percentile(query_times, 95) * 1000
                })
        
        return pd.DataFrame(results)
    
    def analyze_index_properties(self) -> Dict[str, Any]:
        """分析索引属性"""
        properties = {}
        
        for index_name, index in self.indexes.items():
            properties[index_name] = {
                "vector_count": len(index.vectors),
                "dimension": index.dimension,
                "index_type": index.index_type.value,
                "memory_usage_mb": self._estimate_memory_usage(index),
                "build_time": self.comparison_results.get(index_name, {}).get("build_time", 0)
            }
            
            # 添加特定索引类型的属性
            if hasattr(index, 'nlist'):
                properties[index_name]["nlist"] = index.nlist
            if hasattr(index, 'M'):
                properties[index_name]["M"] = index.M
                
        return properties
    
    def get_comparison_report(self) -> Dict[str, Any]:
        """生成比较报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "index_properties": self.analyze_index_properties(),
            "recommendations": self._generate_recommendations()
        }
    
    def _estimate_memory_usage(self, index: VectorIndex) -> float:
        """估算内存使用（MB）"""
        if hasattr(index, 'index') and index.index is not None:
            # 尝试获取实际内存使用
            try:
                import psutil
                import os
                process = psutil.Process(os.getpid())
                return process.memory_info().rss / 1024 / 1024
            except:
                pass
        
        # 粗略估算
        vector_memory = len(index.vectors) * index.dimension * 4 / 1024 / 1024  # float32
        return vector_memory
    
    def _calculate_recall(self, results: List[Dict], ground_truth: List[Dict]) -> float:
        """计算召回率"""
        result_ids = {r["id"] for r in results}
        truth_ids = {r["id"] for r in ground_truth}
        
        if not truth_ids:
            return 1.0
        
        intersection = result_ids.intersection(truth_ids)
        return len(intersection) / len(truth_ids)
    
    def _generate_recommendations(self) -> List[str]:
        """生成索引选择建议"""
        recommendations = []
        
        if "hnsw" in self.indexes:
            recommendations.append("HNSW索引适合高精度和高查询性能场景")
        if "ivf_flat" in self.indexes:
            recommendations.append("IVF_FLAT索引在亿级向量规模下具有较好的平衡性")
        if "flat" in self.indexes:
            recommendations.append("FLAT索引适合小规模数据（<10万）或需要100%召回率的场景")
        if "annoy" in self.indexes:
            recommendations.append("Annoy索引适合内存受限的只读场景")
            
        return recommendations
