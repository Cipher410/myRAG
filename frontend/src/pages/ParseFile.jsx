import React, { useState } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const ParseFile = () => {
  // 文件与模式
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('structured'); // 'traditional' or 'structured'

  // 传统解析参数
  const [loadingMethod, setLoadingMethod] = useState('pymupdf');
  const [parsingOption, setParsingOption] = useState('all_text');

  // 结构化解析参数
  const [strategy, setStrategy] = useState('hi_res');

  // 状态与结果
  const [parsedContent, setParsedContent] = useState(null);
  const [structuredDoc, setStructuredDoc] = useState(null);
  const [status, setStatus] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setParsedContent(null);
      setStructuredDoc(null);
      setStatus('');
    }
  };

  // 传统解析
  const handleTraditionalParse = async () => {
    if (!file) {
      setStatus('请选择 PDF 文件');
      return;
    }
    setIsProcessing(true);
    setStatus('正在解析（传统模式）...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('loading_method', loadingMethod);
    formData.append('parsing_option', parsingOption);

    try {
      const response = await fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setParsedContent(data.parsed_content);
      setStructuredDoc(null);
      setStatus('传统解析完成');
    } catch (err) {
      console.error(err);
      setStatus(`传统解析失败: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // 结构化解析
  const handleStructuredParse = async () => {
    if (!file) {
      setStatus('请选择 PDF 文件');
      return;
    }
    setIsProcessing(true);
    setStatus('正在结构化解析（unstructured）...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('strategy', strategy);
    formData.append('save_to_disk', 'true');

    try {
      const response = await fetch(`${apiBaseUrl}/parse-structured`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setStructuredDoc(data.structured_document);
      setParsedContent(null);
      setStatus(`结构化解析完成，已保存至 ${data.saved_path || '服务器'}`);
    } catch (err) {
      console.error(err);
      setStatus(`结构化解析失败: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // 递归渲染章节树
  const renderSections = (sections, depth = 0) => {
    return sections.map((section, idx) => (
      <div key={idx} style={{ marginLeft: depth * 20, marginBottom: 12 }}>
        <div className="font-bold text-gray-800" style={{ fontSize: 16 - Math.min(depth, 3) }}>
          {section.title} (Level {section.level})
        </div>
        <div className="text-sm text-gray-600 mt-1 space-y-1">
          {section.content.slice(0, 5).map((item, i) => (
            <div key={i} className="border-l-2 border-blue-300 pl-2">
              <span className="font-mono text-xs text-gray-500">[{item.type}]</span>{' '}
              {item.type === 'table' ? (
                <details>
                  <summary className="cursor-pointer text-blue-600">查看表格 (Markdown)</summary>
                  <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-auto">
                    {item.markdown || item.text}
                  </pre>
                </details>
              ) : (
                <span>{item.text?.substring(0, 200)}{item.text?.length > 200 ? '…' : ''}</span>
              )}
            </div>
          ))}
          {section.content.length > 5 && (
            <div className="text-gray-400 text-xs">…… 还有 {section.content.length - 5} 个元素</div>
          )}
        </div>
        {section.subsections?.length > 0 && renderSections(section.subsections, depth + 1)}
      </div>
    ));
  };

  // 右侧展示内容
  const renderRightPanel = () => {
    if (mode === 'traditional' && parsedContent) {
      return (
        <div className="p-4">
          <h3 className="text-xl font-semibold mb-4">传统解析结果</h3>
          <div className="mb-4 p-3 border rounded bg-gray-100">
            <h4 className="font-medium mb-2">文档信息</h4>
            <div className="text-sm text-gray-600">
              <p>总页数: {parsedContent.metadata?.total_pages}</p>
              <p>解析方法: {parsedContent.metadata?.parsing_method}</p>
              <p>时间戳: {parsedContent.metadata?.timestamp && new Date(parsedContent.metadata.timestamp).toLocaleString()}</p>
            </div>
          </div>
          <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
            {parsedContent.content.map((item, idx) => (
              <div key={idx} className="p-3 border rounded bg-gray-50">
                <div className="font-medium text-sm text-gray-500 mb-1">
                  {item.type} - 第 {item.page} 页
                </div>
                {item.title && <div className="font-bold text-gray-700 mb-2">{item.title}</div>}
                <div className="text-sm text-gray-600 whitespace-pre-wrap">{item.content}</div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (mode === 'structured' && structuredDoc) {
      return (
        <div className="p-4">
          <h3 className="text-xl font-semibold mb-4">结构化解析结果（基于 Unstructured）</h3>
          <div className="mb-4 p-3 border rounded bg-gray-100">
            <h4 className="font-medium mb-2">文档元数据</h4>
            <div className="text-sm text-gray-600">
              <p>文件名: {structuredDoc.metadata?.filename}</p>
              <p>元素总数: {structuredDoc.metadata?.total_elements}</p>
            </div>
          </div>
          <div className="max-h-[calc(100vh-320px)] overflow-y-auto">
            {structuredDoc.sections?.length > 0 ? (
              renderSections(structuredDoc.sections)
            ) : (
              <p className="text-gray-500">未检测到章节结构</p>
            )}
          </div>
        </div>
      );
    }

    return (
      <RandomImage
        message={
          mode === 'structured'
            ? '上传 PDF 并点击「结构化解析」，查看按标题、表格提取的文档树'
            : '上传 PDF 并点击「传统解析」，查看按页面/标题/表格规则提取的内容'
        }
      />
    );
  };

  return (
    <div className="p-6">
      <h1 className="text-blue-500 text-3xl font-bold text-center mb-6">检索增强生成工具</h1>
      <hr />
      <h2 className="text-2xl font-bold mb-6">文件解析（支持结构化解析）</h2>

      <div className="grid grid-cols-12 gap-6">
        {/* 左侧控制面板 */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div>
              <label className="block text-sm font-medium mb-1">选择 PDF 文件</label>
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="block w-full border rounded px-3 py-2"
                required
              />
            </div>

            {/* 模式切换 */}
            <div className="mt-4">
              <label className="block text-sm font-medium mb-1">解析模式</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setMode('structured')}
                  className={`flex-1 py-1 rounded ${
                    mode === 'structured'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  结构化解析
                </button>
                <button
                  type="button"
                  onClick={() => setMode('traditional')}
                  className={`flex-1 py-1 rounded ${
                    mode === 'traditional'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  传统解析
                </button>
              </div>
            </div>

            {/* 结构化解析参数 */}
            {mode === 'structured' && (
              <div className="mt-4">
                <label className="block text-sm font-medium mb-1">解析策略</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  <option value="fast">Fast (速度快)</option>
                  <option value="hi_res">Hi-Res (高精度，推荐)</option>
                  <option value="ocr_only">OCR Only (适合扫描件)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  使用 Unstructured 库，可提取标题、表格、段落等结构化信息。
                </p>
              </div>
            )}

            {/* 传统解析参数 */}
            {mode === 'traditional' && (
              <>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-1">装载工具</label>
                  <select
                    value={loadingMethod}
                    onChange={(e) => setLoadingMethod(e.target.value)}
                    className="block w-full p-2 border rounded"
                  >
                    <option value="pymupdf">PyMuPDF</option>
                    <option value="pypdf">PyPDF</option>
                    <option value="unstructured">Unstructured</option>
                    <option value="pdfplumber">PDF Plumber</option>
                  </select>
                </div>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-1">解析选项</label>
                  <select
                    value={parsingOption}
                    onChange={(e) => setParsingOption(e.target.value)}
                    className="block w-full p-2 border rounded"
                  >
                    <option value="all_text">All Text</option>
                    <option value="by_pages">By Pages</option>
                    <option value="by_titles">By Titles</option>
                    <option value="text_and_tables">Text and Tables</option>
                  </select>
                </div>
              </>
            )}

            <button
              onClick={mode === 'structured' ? handleStructuredParse : handleTraditionalParse}
              disabled={!file || isProcessing}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
            >
              {isProcessing ? '解析中...' : mode === 'structured' ? '开始结构化解析' : '开始传统解析'}
            </button>

            {status && (
              <div
                className={`mt-4 p-3 rounded text-sm ${
                  status.includes('失败') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                }`}
              >
                {status}
              </div>
            )}
          </div>
        </div>

        {/* 右侧结果展示 */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {renderRightPanel()}
        </div>
      </div>
    </div>
  );
};

export default ParseFile;