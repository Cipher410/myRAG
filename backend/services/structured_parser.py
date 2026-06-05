import logging
from typing import List, Dict, Any, Optional
import re
import pandas as pd
from io import StringIO
from unstructured.documents.elements import Element, Title, NarrativeText, Table, ListItem, FigureCaption

logger = logging.getLogger(__name__)

class StructuredParser:
    """
    将 unstructured 元素列表转换为结构化的文档树（标题层级 + 内容块）
    表格自动转换为 Markdown 格式
    """

    def parse(self, elements: List[Element], filename: str = "") -> Dict[str, Any]:
        """
        解析元素列表，生成文档结构
        返回格式:
        {
            "metadata": {"filename": ..., "total_elements": ...},
            "sections": [
                {
                    "title": "Abstract",
                    "level": 1,
                    "content": [{"type": "text", "text": "..."}, ...],
                    "subsections": [...]
                },
                ...
            ]
        }
        """
        sections = []
        stack = []  # 每个元素为 {"level": int, "section": dict}

        for el in elements:
            if isinstance(el, Title):
                # 获取标题层级，处理 None 的情况
                level_raw = getattr(el.metadata, 'category_depth', 1)
                if level_raw is None:
                    level = 1
                else:
                    level = int(level_raw)
                title_text = self._clean_text(str(el))
                new_section = {
                    "title": title_text,
                    "level": level,
                    "content": [],
                    "subsections": []
                }
                # 弹出栈中层级 >= 当前层级的元素
                while stack and stack[-1]["level"] >= level:
                    stack.pop()
                if stack:
                    stack[-1]["section"]["subsections"].append(new_section)
                    stack.append({"level": level, "section": new_section})
                else:
                    sections.append(new_section)
                    stack.append({"level": level, "section": new_section})
            else:
                current_section = stack[-1]["section"] if stack else None
                if current_section is None:
                    default_section = {
                        "title": "Introduction",
                        "level": 1,
                        "content": [],
                        "subsections": []
                    }
                    sections.append(default_section)
                    stack.append({"level": 1, "section": default_section})
                    current_section = default_section

                content_item = self._convert_element(el)
                if content_item:
                    current_section["content"].append(content_item)

        return {
            "metadata": {
                "filename": filename,
                "total_elements": len(elements)
            },
            "sections": sections
        }

    def _convert_element(self, el: Element) -> Optional[Dict[str, Any]]:
        """将单个 unstructured 元素转换为统一的内容字典"""
        text = self._clean_text(str(el))
        if not text:
            return None

        if isinstance(el, NarrativeText):
            return {"type": "text", "text": text}
        elif isinstance(el, Table):
            md_table = self._table_to_markdown(el)
            return {"type": "table", "markdown": md_table, "text": text}
        elif isinstance(el, ListItem):
            return {"type": "list_item", "text": text}
        elif isinstance(el, FigureCaption):
            return {"type": "caption", "text": text}
        else:
            if text.strip():
                return {"type": "other", "text": text}
            return None

    def _table_to_markdown(self, table_element: Table) -> str:
        """
        将 unstructured 的 Table 元素转换为 Markdown 表格字符串
        """
        raw_text = str(table_element)
        # 尝试解析 HTML 表格
        if '<table' in raw_text.lower():
            try:
                dfs = pd.read_html(StringIO(raw_text))
                if dfs:
                    return dfs[0].to_markdown(index=False)
            except Exception as e:
                logger.warning(f"Failed to parse HTML table: {e}")
        # 尝试解析 CSV 格式
        try:
            if '|' in raw_text and '---' in raw_text:
                return raw_text
            df = pd.read_csv(StringIO(raw_text), sep=None, engine='python')
            if df is not None and not df.empty:
                return df.to_markdown(index=False)
        except Exception:
            pass
        return raw_text

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()