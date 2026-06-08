"""
检索前优化和检索后优化服务
"""
import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import Counter

class RetrievalOptimizationService:
    """检索优化服务 - 包含检索前和检索后优化"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service  # 可选的LLM服务用于重写
        self.stop_words = set(['的', '了', '是', '在', '和', '与', '或', '有', '没有', '这', '那', '不', '也'])
        
    # ========== 检索前优化 ==========
    
    def pre_retrieval_optimization(self, query: str) -> Dict[str, Any]:
        """
        检索前优化主流程
        """
        optimization_result = {
            "original_query": query,
            "query_rewrites": [],
            "query_expansion": [],
            "query_cleanup": None,
            "optimized_queries": []
        }
        
        # 1. 查询清理
        cleaned_query = self._clean_query(query)
        optimization_result["query_cleanup"] = cleaned_query
        
        # 2. 查询重写（生成多个变体）
        rewrites = self._rewrite_query(cleaned_query)
        optimization_result["query_rewrites"] = rewrites
        
        # 3. 查询扩展
        expansions = self._expand_query(cleaned_query)
        optimization_result["query_expansion"] = expansions
        
        # 4. 生成优化后的查询
        optimized = self._generate_optimized_queries(cleaned_query, rewrites, expansions)
        optimization_result["optimized_queries"] = optimized
        
        return optimization_result
    
    def _clean_query(self, query: str) -> str:
        """查询清理：去除噪声词、标点规范化"""
        # 去除特殊字符
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        # 去除多余空格
        cleaned = ' '.join(cleaned.split())
        # 去除停止词（可选）
        cleaned = ' '.join([word for word in cleaned.split() if word not in self.stop_words])
        return cleaned
    
    def _rewrite_query(self, query: str) -> List[str]:
        """查询重写：生成语义相似的查询变体"""
        rewrites = [query]
        
        # 如果LLM服务可用，使用LLM生成重写
        if self.llm_service:
            try:
                llm_rewrites = self._llm_rewrite(query)
                rewrites.extend(llm_rewrites)
            except:
                pass
        
        # 基于规则的重写
        # 1. 同义词替换（简化版，可扩展为同义词词典）
        synonym_map = {
            "如何": ["怎么", "怎样"],
            "为什么": ["为何", "是什么原因"],
            "区别": ["差异", "不同"],
        }
        
        for original, synonyms in synonym_map.items():
            if original in query:
                for syn in synonyms:
                    rewrites.append(query.replace(original, syn))
        
        # 2. 关键词提取后重写
        keywords = self._extract_keywords(query)
        if keywords:
            rewrites.append(' '.join(keywords))
            
        return list(set(rewrites))  # 去重
    
    def _expand_query(self, query: str) -> List[str]:
        """查询扩展：添加相关词增强检索"""
        expansions = []
        
        # 1. 添加同义词
        synonyms = self._get_synonyms(query)
        if synonyms:
            expansions.extend(synonyms)
        
        # 2. 添加相关概念（可基于知识图谱或LLM）
        related_concepts = self._get_related_concepts(query)
        if related_concepts:
            expansions.extend(related_concepts)
        
        # 3. 添加权重调整
        expansions.append(self._add_term_weights(query))
        
        return list(set(expansions))
    
    def _extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """提取关键词"""
        # 简单实现：基于TF-IDF，这里用简单统计
        words = text.split()
        word_freq = Counter(words)
        keywords = [word for word, _ in word_freq.most_common(top_k)]
        return keywords
    
    def _get_synonyms(self, query: str) -> List[str]:
        """获取同义词（简化版，可集成同义词库）"""
        synonyms_dict = {
            "快速": ["高效", "迅速"],
            "准确": ["精确", "精准"],
            "分析": ["解析", "剖析"],
        }
        
        synonyms = []
        for word in query.split():
            if word in synonyms_dict:
                synonyms.extend(synonyms_dict[word])
        return synonyms
    
    def _get_related_concepts(self, query: str) -> List[str]:
        """获取相关概念"""
        # 简化实现，实际可调用知识图谱API
        concept_map = {
            "RAG": ["检索增强生成", "Retrieval Augmented Generation", "向量检索"],
            "向量": ["embedding", "向量化", "特征向量"],
        }
        
        concepts = []
        for word in query.split():
            if word in concept_map:
                concepts.extend(concept_map[word])
        return concepts
    
    def _add_term_weights(self, query: str) -> str:
        """为关键术语添加权重"""
        keywords = self._extract_keywords(query, top_k=3)
        weighted_terms = [f"{kw}^2" for kw in keywords]
        return ' '.join(weighted_terms)
    
    def _llm_rewrite(self, query: str) -> List[str]:
        """使用LLM重写查询"""
        # 如果配置了LLM，可以调用
        # 这里提供接口，实际需要集成具体LLM服务
        prompt = f"请用3种不同方式重写以下查询，保持原意：{query}"
        # response = self.llm_service.generate(prompt)
        # 解析响应返回重写列表
        return []  # 占位实现
    
    def _generate_optimized_queries(self, original: str, rewrites: List[str], expansions: List[str]) -> List[str]:
        """生成最终优化查询"""
        optimized = [original]
        
        # 合并重写
        optimized.extend(rewrites[1:5])  # 限制数量
        
        # 添加扩展查询
        if expansions:
            expanded_query = original + ' ' + ' '.join(expansions[:3])
            optimized.append(expanded_query)
            
        return optimized
    
    # ========== 检索后优化 ==========
    
    def post_retrieval_optimization(self, 
                                   query: str,
                                   retrieved_docs: List[Dict],
                                   top_k: int = 5) -> Dict[str, Any]:
        """
        检索后优化主流程
        """
        optimization_result = {
            "original_query": query,
            "original_docs_count": len(retrieved_docs),
            "reranked_docs": [],
            "filtered_docs": [],
            "document_clusters": [],
            "optimized_docs": []
        }
        
        # 1. 文档重排序
        reranked = self._rerank_documents(query, retrieved_docs)
        optimization_result["reranked_docs"] = reranked[:top_k]
        
        # 2. 文档过滤
        filtered = self._filter_documents(query, reranked)
        optimization_result["filtered_docs"] = filtered[:top_k]
        
        # 3. 去重和聚类
        clusters = self._cluster_documents(reranked)
        optimization_result["document_clusters"] = clusters
        
        # 4. 内容增强（提取关键片段）
        enhanced = self._enhance_content(filtered[:top_k])
        optimization_result["optimized_docs"] = enhanced
        
        return optimization_result
    
    def _rerank_documents(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        文档重排序 - 使用交叉编码器或多维度打分
        """
        # 计算每个文档的综合得分
        for doc in documents:
            # 1. 原始相似度分数（0-1）
            original_score = doc.get('score', 0.5)
            
            # 2. 文本匹配分数
            text_match_score = self._compute_text_match(query, doc.get('content', ''))
            
            # 3. 关键术语覆盖度
            keyword_coverage = self._compute_keyword_coverage(query, doc.get('content', ''))
            
            # 4. 文档新鲜度（如果有时间戳）
            freshness_score = self._compute_freshness(doc)
            
            # 综合评分（可调整权重）
            final_score = (0.5 * original_score + 
                          0.3 * text_match_score + 
                          0.1 * keyword_coverage +
                          0.1 * freshness_score)
            
            doc['rerank_score'] = final_score
            doc['score_breakdown'] = {
                'similarity': original_score,
                'text_match': text_match_score,
                'keyword_coverage': keyword_coverage,
                'freshness': freshness_score
            }
        
        # 按新分数排序
        reranked = sorted(documents, key=lambda x: x.get('rerank_score', 0), reverse=True)
        return reranked
    
    def _compute_text_match(self, query: str, content: str) -> float:
        """计算文本匹配度"""
        query_terms = set(query.lower().split())
        content_terms = set(content.lower().split())
        
        if not query_terms:
            return 0.0
            
        intersection = query_terms.intersection(content_terms)
        return len(intersection) / len(query_terms)
    
    def _compute_keyword_coverage(self, query: str, content: str) -> float:
        """计算关键词覆盖度"""
        keywords = self._extract_keywords(query, top_k=5)
        if not keywords:
            return 0.0
            
        content_lower = content.lower()
        covered = sum(1 for kw in keywords if kw in content_lower)
        return covered / len(keywords)
    
    def _compute_freshness(self, doc: Dict) -> float:
        """计算文档新鲜度（如果有时间信息）"""
        # 检查文档中是否有时间戳
        if 'timestamp' in doc:
            # 简化的新鲜度计算，实际可基于时间差
            return 0.8
        return 0.5  # 默认中等新鲜度
    
    def _filter_documents(self, query: str, documents: List[Dict]) -> List[Dict]:
        """过滤低质量或重复文档"""
        filtered = []
        seen_content = set()
        
        for doc in documents:
            content_preview = doc.get('content', '')[:200]
            
            # 去重
            if content_preview in seen_content:
                continue
            seen_content.add(content_preview)
            
            # 相关度阈值过滤
            if doc.get('rerank_score', 0) > 0.3:
                filtered.append(doc)
                
        return filtered
    
    def _cluster_documents(self, documents: List[Dict]) -> List[Dict]:
        """文档聚类（简化版）"""
        # 实际可使用聚类算法如KMeans
        clusters = []
        
        # 简单实现：基于关键词聚类
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            keywords = self._extract_keywords(content, top_k=3)
            
            # 查找相似文档
            cluster = [{
                'doc_id': doc.get('id', i),
                'keywords': keywords,
                'score': doc.get('rerank_score', 0)
            }]
            clusters.append({
                'cluster_id': i,
                'documents': cluster,
                'representative_keywords': keywords
            })
            
        return clusters
    
    def _enhance_content(self, documents: List[Dict]) -> List[Dict]:
        """内容增强：提取关键片段、摘要"""
        enhanced = []
        
        for doc in documents:
            content = doc.get('content', '')
            
            # 提取关键句子
            key_sentences = self._extract_key_sentences(content, top_k=2)
            
            # 生成简短摘要
            summary = self._generate_summary(content)
            
            enhanced_doc = doc.copy()
            enhanced_doc['key_sentences'] = key_sentences
            enhanced_doc['summary'] = summary
            enhanced.append(enhanced_doc)
            
        return enhanced
    
    def _extract_key_sentences(self, text: str, top_k: int = 2) -> List[str]:
        """提取关键句子"""
        # 按句号分割
        sentences = re.split(r'[。!?]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return [text[:200]]
            
        # 简单打分：包含关键词多的句子得分高
        keywords = self._extract_keywords(text, top_k=10)
        scored_sentences = []
        
        for sent in sentences:
            score = sum(1 for kw in keywords if kw in sent)
            scored_sentences.append((sent, score))
            
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sent for sent, _ in scored_sentences[:top_k]]
    
    def _generate_summary(self, text: str, max_length: int = 100) -> str:
        """生成简短摘要"""
        if len(text) <= max_length:
            return text
            
        # 简单的截取方式，取前几个完整句子
        truncated = text[:max_length]
        last_period = truncated.rfind('。')
        if last_period > max_length * 0.5:
            return truncated[:last_period + 1]
        
        return truncated + '...'
