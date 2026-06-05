from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf
import pdfplumber
import fitz  # PyMuPDF
import logging
import os
from datetime import datetime
import json
import pytesseract
import sys
import nltk

# 设置自定义 NLTK 数据路径（永久生效）
custom_nltk_path = r'D:\nltk_data'   # 请替换为您的实际路径
nltk.data.path.insert(0, custom_nltk_path)   # 插入到最前面，优先查找

# 可选：同时设置环境变量（某些子进程需要）
os.environ['NLTK_DATA'] = custom_nltk_path
# 如果是在 Conda 虚拟环境中，可以同时设置 PATH
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract_OCR\tesseract.exe'

logger = logging.getLogger(__name__)

class LoadingService:
    """
    PDF文档加载服务类
    提供多种PDF文档加载方法，并支持结构化元素提取（unstructured）
    """

    def __init__(self):
        self.total_pages = 0
        self.current_page_map = []

    def load_pdf(self, file_path: str, method: str, strategy: str = None, chunking_strategy: str = None, chunking_options: dict = None) -> str:
        """加载PDF文档，返回纯文本（原有逻辑）"""
        try:
            if method == "pymupdf":
                return self._load_with_pymupdf(file_path)
            elif method == "pypdf":
                return self._load_with_pypdf(file_path)
            elif method == "pdfplumber":
                return self._load_with_pdfplumber(file_path)
            elif method == "unstructured":
                return self._load_with_unstructured(
                    file_path,
                    strategy=strategy,
                    chunking_strategy=chunking_strategy,
                    chunking_options=chunking_options
                )
            else:
                raise ValueError(f"Unsupported loading method: {method}")
        except Exception as e:
            logger.error(f"Error loading PDF with {method}: {str(e)}")
            raise

    def load_pdf_structured(self, file_path: str, strategy: str = "hi_res") -> list:
        """
        使用 unstructured 加载 PDF，返回原始元素列表（结构化）
        参数:
            file_path: PDF文件路径
            strategy: 解析策略，'fast', 'hi_res', 'ocr_only'
        返回:
            List[unstructured.documents.elements.Element] 元素列表
        """
        from unstructured.partition.pdf import partition_pdf
        elements = partition_pdf(
            filename=file_path,
            strategy=strategy,
            infer_table_structure=True,  # 表格结构识别
            extract_images_in_pdf=False,
            #extract_tables=False,  # 不提取表格
            #skip_infer_table_types=[]  # 或者不开启表格推断
        )
        logger.info(f"Loaded {len(elements)} structured elements from {file_path}")
        return elements

    def get_total_pages(self) -> int:
        return max(page_data['page'] for page_data in self.current_page_map) if self.current_page_map else 0

    def get_page_map(self) -> list:
        return self.current_page_map

    def _load_with_pymupdf(self, file_path: str) -> str:
        text_blocks = []
        with fitz.open(file_path) as doc:
            self.total_pages = len(doc)
            for page_num, page in enumerate(doc, 1):
                text = page.get_text("text")
                if text.strip():
                    text_blocks.append({"text": text.strip(), "page": page_num})
        self.current_page_map = text_blocks
        return "\n".join(block["text"] for block in text_blocks)

    def _load_with_pypdf(self, file_path: str) -> str:
        text_blocks = []
        with open(file_path, "rb") as file:
            pdf = PdfReader(file)
            self.total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_blocks.append({"text": page_text.strip(), "page": page_num})
        self.current_page_map = text_blocks
        return "\n".join(block["text"] for block in text_blocks)

    def _load_with_unstructured(self, file_path: str, strategy: str = "fast", chunking_strategy: str = "basic", chunking_options: dict = None) -> str:
        try:
            strategy_params = {
                "fast": {"strategy": "fast"},
                "hi_res": {"strategy": "hi_res"},
                "ocr_only": {"strategy": "ocr_only"}
            }
            chunking_params = {}
            if chunking_strategy == "basic":
                chunking_params = {
                    "max_characters": chunking_options.get("maxCharacters", 4000),
                    "new_after_n_chars": chunking_options.get("newAfterNChars", 3000),
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "overlap": chunking_options.get("overlap", 200),
                    "overlap_all": chunking_options.get("overlapAll", False)
                }
            elif chunking_strategy == "by_title":
                chunking_params = {
                    "chunking_strategy": "by_title",
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "multipage_sections": chunking_options.get("multiPageSections", False)
                }
            params = {**strategy_params.get(strategy, {"strategy": "fast"}), **chunking_params}
            elements = partition_pdf(file_path, **params)
            text_blocks = []
            pages = set()
            for elem in elements:
                metadata = elem.metadata.__dict__
                page_number = metadata.get('page_number')
                if page_number is not None:
                    pages.add(page_number)
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if key == '_known_field_names':
                            continue
                        try:
                            json.dumps({key: value})
                            cleaned_metadata[key] = value
                        except (TypeError, OverflowError):
                            cleaned_metadata[key] = str(value)
                    cleaned_metadata['element_type'] = elem.__class__.__name__
                    cleaned_metadata['id'] = str(getattr(elem, 'id', None))
                    cleaned_metadata['category'] = str(getattr(elem, 'category', None))
                    text_blocks.append({
                        "text": str(elem),
                        "page": page_number,
                        "metadata": cleaned_metadata
                    })
            self.total_pages = max(pages) if pages else 0
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"Unstructured error: {str(e)}")
            raise

    def _load_with_pdfplumber(self, file_path: str) -> str:
        text_blocks = []
        with pdfplumber.open(file_path) as pdf:
            self.total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_blocks.append({"text": page_text.strip(), "page": page_num})
        self.current_page_map = text_blocks
        return "\n".join(block["text"] for block in text_blocks)

    def save_document(self, filename: str, chunks: list, metadata: dict, loading_method: str, strategy: str = None, chunking_strategy: str = None) -> str:
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            base_name = filename.replace('.pdf', '').split('_')[0]
            if loading_method == "unstructured" and strategy:
                doc_name = f"{base_name}_{loading_method}_{strategy}_{chunking_strategy}_{timestamp}"
            else:
                doc_name = f"{base_name}_{loading_method}_{timestamp}"
            document_data = {
                "filename": str(filename),
                "total_chunks": int(len(chunks)),
                "total_pages": int(metadata.get("total_pages", 1)),
                "loading_method": str(loading_method),
                "loading_strategy": str(strategy) if loading_method == "unstructured" and strategy else None,
                "chunking_strategy": str(chunking_strategy) if loading_method == "unstructured" and chunking_strategy else None,
                "chunking_method": "loaded",
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks
            }
            filepath = os.path.join("01-loaded-docs", f"{doc_name}.json")
            os.makedirs("01-loaded-docs", exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
            return filepath
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise