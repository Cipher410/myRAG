from datetime import datetime
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class ChunkingService:
    """
    文本分块服务，提供多种文本分块策略
    支持按页面、固定大小、段落、句子以及按标题结构分块
    """

    def chunk_text(self, text: str, method: str, metadata: dict, page_map: list = None, chunk_size: int = 1000, structured_doc: dict = None) -> dict:
        """
        将文本按指定方法分块
        新增：method == "by_headings" 时使用结构化文档进行标题切分
        """
        try:
            if method == "by_headings":
                if not structured_doc:
                    raise ValueError("Structured document required for 'by_headings' chunking")
                chunks = self.chunk_by_headings(structured_doc, max_chunk_size=chunk_size)
                document_data = {
                    "filename": metadata.get("filename", ""),
                    "total_chunks": len(chunks),
                    "total_pages": metadata.get("total_pages", 0),
                    "loading_method": metadata.get("loading_method", ""),
                    "chunking_method": method,
                    "timestamp": datetime.now().isoformat(),
                    "chunks": chunks
                }
                return document_data

            if not page_map:
                raise ValueError("Page map is required for chunking.")

            chunks = []
            total_pages = len(page_map)

            if method == "by_pages":
                for page_data in page_map:
                    chunk_metadata = {
                        "chunk_id": len(chunks) + 1,
                        "page_number": page_data['page'],
                        "page_range": str(page_data['page']),
                        "word_count": len(page_data['text'].split())
                    }
                    chunks.append({
                        "content": page_data['text'],
                        "metadata": chunk_metadata
                    })
            elif method == "fixed_size":
                for page_data in page_map:
                    page_chunks = self._fixed_size_chunks(page_data['text'], chunk_size)
                    for idx, chunk in enumerate(page_chunks, 1):
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data['page'],
                            "page_range": str(page_data['page']),
                            "word_count": len(chunk["text"].split())
                        }
                        chunks.append({
                            "content": chunk["text"],
                            "metadata": chunk_metadata
                        })
            elif method in ["by_paragraphs", "by_sentences"]:
                splitter_method = self._paragraph_chunks if method == "by_paragraphs" else self._sentence_chunks
                for page_data in page_map:
                    page_chunks = splitter_method(page_data['text'])
                    for chunk in page_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data['page'],
                            "page_range": str(page_data['page']),
                            "word_count": len(chunk["text"].split())
                        }
                        chunks.append({
                            "content": chunk["text"],
                            "metadata": chunk_metadata
                        })
            else:
                raise ValueError(f"Unsupported chunking method: {method}")

            document_data = {
                "filename": metadata.get("filename", ""),
                "total_chunks": len(chunks),
                "total_pages": total_pages,
                "loading_method": metadata.get("loading_method", ""),
                "chunking_method": method,
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks
            }
            return document_data

        except Exception as e:
            logger.error(f"Error in chunk_text: {str(e)}")
            raise

    def chunk_by_headings(self, structured_doc: Dict[str, Any], max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        按标题层级切分文档，保证所有内容完整保留（不截断丢弃）。
        策略：
        - 每个子章节独立成块
        - 父章节的直接内容（不含子章节）若长度超过 max_chunk_size，则拆分为多个块（按段落 -> 按句子）
        - 递归处理子章节
        """
        import re
        chunks = []
        chunk_id_counter = 1

        def split_text_into_chunks(text: str, max_len: int) -> List[str]:
            """
            将文本无损拆分为多个不超过 max_len 的片段。
            优先级：段落 -> 句子 -> 强制截断（保持完整单词）。
            """
            if len(text) <= max_len:
                return [text]

            # 1. 尝试按段落拆分（两个换行）
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                result = []
                current = ""
                for para in paragraphs:
                    if len(current) + len(para) + 2 <= max_len:
                        current += (para + "\n\n")
                    else:
                        if current:
                            result.append(current.strip())
                        # 如果单个段落超过 max_len，则递归按句子拆分
                        if len(para) > max_len:
                            result.extend(split_text_into_chunks(para, max_len))
                        else:
                            current = para + "\n\n"
                if current:
                    result.append(current.strip())
                return result

            # 2. 按句子拆分（中文英文句子分隔符）
            sentences = re.split(r'(?<=[。！？；.!?;])\s+', text)
            if len(sentences) > 1:
                result = []
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_len:
                        current += (sent + " ")
                    else:
                        if current:
                            result.append(current.strip())
                        # 单个句子超过 max_len，强制按单词截断
                        if len(sent) > max_len:
                            words = sent.split()
                            sub_current = ""
                            for w in words:
                                if len(sub_current) + len(w) + 1 <= max_len:
                                    sub_current += (w + " ")
                                else:
                                    if sub_current:
                                        result.append(sub_current.strip())
                                    sub_current = w + " "
                            if sub_current:
                                result.append(sub_current.strip())
                        else:
                            current = sent + " "
                if current:
                    result.append(current.strip())
                return result

            # 3. 强制按字符截断（保留单词完整性）
            words = text.split()
            result = []
            current = ""
            for w in words:
                if len(current) + len(w) + 1 <= max_len:
                    current += (w + " ")
                else:
                    if current:
                        result.append(current.strip())
                    current = w + " "
            if current:
                result.append(current.strip())
            return result

        def build_content(section: Dict[str, Any]) -> str:
            """收集章节的直接内容（不含子章节）"""
            parts = []
            for item in section.get("content", []):
                if item["type"] == "text":
                    parts.append(item["text"])
                elif item["type"] == "table":
                    parts.append(item.get("markdown", item.get("text", "")))
                elif item["type"] in ("list_item", "caption", "other"):
                    parts.append(item["text"])
            return "\n\n".join(parts)

        def create_chunk(content: str, section: Dict[str, Any], parent_title: str, chunk_id: int) -> Dict:
            word_count = len(content.split())
            full_title = f"{parent_title} > {section['title']}" if parent_title else section['title']
            return {
                "content": content,
                "metadata": {
                    "chunk_id": chunk_id,
                    "page_number": "0",
                    "page_range": "0",
                    "word_count": word_count,
                    "title": full_title,
                    "heading_level": section["level"],
                    "parent_title": parent_title,
                    "chunk_type": "heading"
                }
            }

        def traverse(section: Dict[str, Any], parent_title: str = ""):
            nonlocal chunk_id_counter
            # 1. 处理当前章节的直接内容（不含子章节）
            direct_content = build_content(section)
            if direct_content.strip():
                content_chunks = split_text_into_chunks(direct_content, max_chunk_size)
                for content in content_chunks:
                    chunks.append(create_chunk(content, section, parent_title, chunk_id_counter))
                    chunk_id_counter += 1

            # 2. 递归处理子章节（每个子章节独立成块）
            current_full_title = f"{parent_title} > {section['title']}" if parent_title else section['title']
            for sub in section.get("subsections", []):
                traverse(sub, current_full_title)

        for section in structured_doc.get("sections", []):
            traverse(section, "")

        return chunks

    def _fixed_size_chunks(self, text: str, chunk_size: int) -> list:
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        for word in words:
            word_length = len(word) + (1 if current_length > 0 else 0)
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append({"text": " ".join(current_chunk)})
                current_chunk = []
                current_length = 0
            current_chunk.append(word)
            current_length += word_length
        if current_chunk:
            chunks.append({"text": " ".join(current_chunk)})
        return chunks

    def _paragraph_chunks(self, text: str) -> list:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return [{"text": para} for para in paragraphs]

    def _sentence_chunks(self, text: str) -> list:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=[".", "!", "?", "\n", " "]
        )
        texts = splitter.split_text(text)
        return [{"text": t} for t in texts]