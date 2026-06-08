"""
向量索引工厂 - 支持多种索引类型
"""
import numpy as np
from typing import List, Dict, Any, Optional
import pickle
import os
from enum import Enum

class IndexType(Enum):
    FLAT = "flat"           # 暴力搜索
    IVF_FLAT = "ivf_flat"   # IVF扁平索引
    IVF_SQ8 = "ivf_sq8"     # IVF标量量化
    HNSW = "hnsw"           # 层次可导航小世界图
    ANNOY = "annoy"         # 近似最近邻

class VectorIndex:
    """向量索引基类"""
    def __init__(self, dimension: int, index_type: IndexType):
        self.dimension = dimension
        self.index_type = index_type
        self.vectors = []
        self.ids = []
        self.index = None
        
    def add_vectors(self, vectors: List[np.ndarray], ids: List[str]):
        """添加向量到索引"""
        self.vectors.extend(vectors)
        self.ids.extend(ids)
        self._build_index()
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict]:
        """搜索相似向量"""
        raise NotImplementedError
    
    def _build_index(self):
        """构建索引"""
        raise NotImplementedError

class FlatIndex(VectorIndex):
    """暴力搜索索引"""
    def __init__(self, dimension: int):
        super().__init__(dimension, IndexType.FLAT)
        
    def _build_index(self):
        # FLAT索引不需要额外构建
        pass
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict]:
        if not self.vectors:
            return []
        
        # 计算余弦相似度
        similarities = []
        query_norm = np.linalg.norm(query_vector)
        
        for i, vec in enumerate(self.vectors):
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0 or query_norm == 0:
                sim = 0
            else:
                sim = np.dot(query_vector, vec) / (query_norm * vec_norm)
            similarities.append((i, sim))
        
        # 排序并返回top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = []
        for i, sim in similarities[:k]:
            results.append({
                "id": self.ids[i],
                "score": float(sim),
                "vector": self.vectors[i]
            })
        return results

class IVFFlatIndex(VectorIndex):
    """IVF扁平索引"""
    def __init__(self, dimension: int, nlist: int = 100):
        super().__init__(dimension, IndexType.IVF_FLAT)
        self.nlist = nlist
        self.centroids = None
        self.inverted_lists = None
        
    def _build_index(self):
        if len(self.vectors) < self.nlist:
            self.nlist = max(1, len(self.vectors) // 10)
        
        # K-means聚类构建倒排索引
        from sklearn.cluster import KMeans
        vectors_array = np.array(self.vectors)
        kmeans = KMeans(n_clusters=self.nlist, random_state=42)
        labels = kmeans.fit_predict(vectors_array)
        
        self.centroids = kmeans.cluster_centers_
        self.inverted_lists = {i: [] for i in range(self.nlist)}
        
        for idx, label in enumerate(labels):
            self.inverted_lists[label].append(idx)
    
    def search(self, query_vector: np.ndarray, k: int = 10, nprobe: int = 10) -> List[Dict]:
        if not self.vectors:
            return []
        
        # 找到最近的nprobe个聚类中心
        distances_to_centroids = []
        for i, centroid in enumerate(self.centroids):
            dist = np.linalg.norm(query_vector - centroid)
            distances_to_centroids.append((i, dist))
        
        distances_to_centroids.sort(key=lambda x: x[1])
        probe_clusters = [idx for idx, _ in distances_to_centroids[:nprobe]]
        
        # 在选中的聚类中搜索
        candidate_indices = []
        for cluster_idx in probe_clusters:
            candidate_indices.extend(self.inverted_lists.get(cluster_idx, []))
        
        # 计算相似度
        similarities = []
        for idx in candidate_indices:
            vec = self.vectors[idx]
            sim = np.dot(query_vector, vec) / (np.linalg.norm(query_vector) * np.linalg.norm(vec))
            similarities.append((idx, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, sim in similarities[:k]:
            results.append({
                "id": self.ids[idx],
                "score": float(sim),
                "vector": self.vectors[idx]
            })
        return results

class HNSWIndex(VectorIndex):
    """HNSW索引实现"""
    def __init__(self, dimension: int, M: int = 16, ef_construction: int = 200):
        super().__init__(dimension, IndexType.HNSW)
        self.M = M
        self.ef_construction = ef_construction
        self.graph = None
        
    def _build_index(self):
        try:
            import hnswlib
            self.index = hnswlib.Index(space='cosine', dim=self.dimension)
            self.index.init_index(max_elements=len(self.vectors), ef_construction=self.ef_construction, M=self.M)
            vectors_array = np.array(self.vectors).astype(np.float32)
            self.index.add_items(vectors_array, np.arange(len(vectors_array)))
        except ImportError:
            print("hnswlib not installed, falling back to FLAT index")
            self.index = None
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict]:
        if not self.vectors or self.index is None:
            return []
        
        query = query_vector.astype(np.float32).reshape(1, -1)
        labels, distances = self.index.knn_query(query, k=k)
        
        results = []
        for label, distance in zip(labels[0], distances[0]):
            results.append({
                "id": self.ids[label],
                "score": float(1 - distance),  # 转换距离为相似度
                "vector": self.vectors[label]
            })
        return results

class AnnoyIndex(VectorIndex):
    """Annoy索引实现"""
    def __init__(self, dimension: int, n_trees: int = 10):
        super().__init__(dimension, IndexType.ANNOY)
        self.n_trees = n_trees
        
    def _build_index(self):
        try:
            from annoy import AnnoyIndex
            self.index = AnnoyIndex(self.dimension, 'angular')
            for i, vec in enumerate(self.vectors):
                self.index.add_item(i, vec.tolist())
            self.index.build(self.n_trees)
        except ImportError:
            print("annoy not installed, falling back to FLAT index")
            self.index = None
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict]:
        if not self.vectors or self.index is None:
            return []
        
        indices, distances = self.index.get_nns_by_vector(
            query_vector.tolist(), k, include_distances=True
        )
        
        results = []
        for idx, distance in zip(indices, distances):
            results.append({
                "id": self.ids[idx],
                "score": float(1 - distance),
                "vector": self.vectors[idx]
            })
        return results

class IndexFactory:
    """索引工厂类"""
    @staticmethod
    def create_index(index_type: IndexType, dimension: int, **kwargs) -> VectorIndex:
        if index_type == IndexType.FLAT:
            return FlatIndex(dimension)
        elif index_type == IndexType.IVF_FLAT:
            nlist = kwargs.get('nlist', 100)
            return IVFFlatIndex(dimension, nlist)
        elif index_type == IndexType.HNSW:
            M = kwargs.get('M', 16)
            ef_construction = kwargs.get('ef_construction', 200)
            return HNSWIndex(dimension, M, ef_construction)
        elif index_type == IndexType.ANNOY:
            n_trees = kwargs.get('n_trees', 10)
            return AnnoyIndex(dimension, n_trees)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")
