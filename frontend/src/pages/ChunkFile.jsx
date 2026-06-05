import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const ChunkFile = () => {
  const [loadedDocuments, setLoadedDocuments] = useState([]);
  const [structuredDocuments, setStructuredDocuments] = useState([]); // 新增：结构化文档列表
  const [selectedDoc, setSelectedDoc] = useState('');
  const [selectedStructuredDoc, setSelectedStructuredDoc] = useState(''); // 新增：选中的结构化文档
  const [chunkingOption, setChunkingOption] = useState('by_pages');
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunks, setChunks] = useState(null);
  const [status, setStatus] = useState('');
  const [activeTab, setActiveTab] = useState('chunks');
  const [processingStatus, setProcessingStatus] = useState('');
  const [chunkedDocuments, setChunkedDocuments] = useState([]);

  // 获取已加载文档（用于传统分块）和结构化文档列表
  useEffect(() => {
    fetchLoadedDocuments();
    fetchStructuredDocuments();
  }, []);

  const fetchLoadedDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents?type=loaded`);
      const data = await response.json();
      setLoadedDocuments(data.documents);

      const chunkedResponse = await fetch(`${apiBaseUrl}/documents?type=chunked`);
      if (!chunkedResponse.ok) {
        throw new Error(`HTTP error! status: ${chunkedResponse.status}`);
      }
      const chunkedData = await chunkedResponse.json();
      console.log('Chunked documents response:', chunkedData);

      if (!chunkedData.documents || !Array.isArray(chunkedData.documents)) {
        console.error('Invalid chunked documents data:', chunkedData);
        return;
      }

      const chunkedDocsWithDetails = await Promise.all(
        chunkedData.documents.map(async (doc) => {
          try {
            const detailResponse = await fetch(`${apiBaseUrl}/documents/${doc.name}?type=chunked`);
            if (!detailResponse.ok) {
              console.error(`Error fetching details for ${doc.name}:`, detailResponse.status);
              return doc;
            }
            const detailData = await detailResponse.json();
            console.log(`Details for ${doc.name}:`, detailData);

            return {
              ...doc,
              total_pages: detailData.total_pages,
              total_chunks: detailData.total_chunks,
              chunking_method: detailData.chunking_method,
              timestamp: detailData.timestamp
            };
          } catch (error) {
            console.error(`Error processing document ${doc.name}:`, error);
            return doc;
          }
        })
      );

      console.log('Final chunked documents:', chunkedDocsWithDetails);
      setChunkedDocuments(chunkedDocsWithDetails);
    } catch (error) {
      console.error('Error fetching documents:', error);
      setProcessingStatus(`Error fetching documents: ${error.message}`);
    }
  };

  // 新增：获取结构化文档列表（由 /parse-structured 生成的 JSON 文件）
  const fetchStructuredDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/structured-docs`);
      if (!response.ok) {
        console.warn('Structured docs endpoint not available');
        return;
      }
      const data = await response.json();
      setStructuredDocuments(data.documents || []);
    } catch (error) {
      console.error('Error fetching structured documents:', error);
    }
  };

  const handleChunk = async () => {
    // 验证输入
    if (chunkingOption === 'by_headings') {
      if (!selectedStructuredDoc) {
        setStatus('请选择结构化文档');
        return;
      }
    } else {
      if (!selectedDoc) {
        setStatus('请选择一个已加载的文档');
        return;
      }
    }

    setStatus('Processing...');
    setChunks(null);

    try {
      const payload = {
        doc_id: selectedDoc,
        chunking_option: chunkingOption,
        chunk_size: chunkSize,
      };

      // 如果是按标题分块，传递结构化文档 ID
      if (chunkingOption === 'by_headings') {
        payload.structured_doc_id = selectedStructuredDoc;
      }

      const response = await fetch(`${apiBaseUrl}/chunk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Chunk response:', data);

      setChunks({
        filename: data.filename,
        total_pages: data.total_pages,
        total_chunks: data.total_chunks,
        loading_method: data.loading_method,
        chunking_method: data.chunking_method,
        timestamp: data.timestamp,
        chunks: data.chunks
      });

      setStatus('Chunking completed successfully!');
      fetchLoadedDocuments(); // 刷新已分块文档列表

    } catch (error) {
      console.error('Error:', error);
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleDeleteDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}?type=chunked`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setProcessingStatus('Document deleted successfully');
      fetchLoadedDocuments();
      if (selectedDoc === docName) {
        setSelectedDoc('');
        setChunks(null);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setProcessingStatus(`Error deleting document: ${error.message}`);
    }
  };

  const handleViewDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}?type=chunked`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setChunks(data);
      setActiveTab('chunks');
    } catch (error) {
      console.error('Error viewing document:', error);
      setProcessingStatus(`Error viewing document: ${error.message}`);
    }
  };

  const renderRightPanel = () => {
    return (
      <div className="p-4 w-full h-full flex flex-col">
        <div className="flex mb-4 border-b">
          <button
            className={`px-4 py-2 ${
              activeTab === 'chunks'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('chunks')}
          >
            分块预览
          </button>
          <button
            className={`px-4 py-2 ml-4 ${
              activeTab === 'documents'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            分块管理
          </button>
        </div>

        {activeTab === 'chunks' ? (
          chunks ? (
            <div className="w-full">
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2">Document Information</h4>
                <div className="text-sm text-gray-600">
                  <p>Filename: {chunks.filename}</p>
                  <p>Total Pages: {chunks.total_pages}</p>
                  <p>Total Chunks: {chunks.total_chunks}</p>
                  <p>Loading Method: {chunks.loading_method}</p>
                  <p>Chunking Method: {chunks.chunking_method}</p>
                  <p>Timestamp: {chunks.timestamp ? new Date(chunks.timestamp).toLocaleString() : 'N/A'}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {Array.isArray(chunks.chunks) && chunks.chunks.map((chunk, idx) => (
                  <div key={idx} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      {chunk.metadata?.title ? `[${chunk.metadata.title}]` : `Chunk ${chunk.metadata?.chunk_id || idx+1}`}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      {chunk.metadata?.page_range && `Pages: ${chunk.metadata.page_range} | `}
                      Words: {chunk.metadata?.word_count || chunk.content.split(/\s+/).length}
                    </div>
                    <div className="text-sm mt-2">
                      <div className="text-gray-600 whitespace-pre-wrap">{chunk.content.substring(0, 500)}{chunk.content.length > 500 && '...'}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="Select a document and create chunks to see the results here" />
          )
        ) : (
          <div className="flex flex-col w-full h-full">
            <h3 className="text-xl font-semibold mb-4">Document Management</h3>
            <div className="space-y-4 w-full">
              {chunkedDocuments.length > 0 ? (
                chunkedDocuments.map((doc) => (
                  <div key={doc.name} className="p-4 border rounded-lg bg-gray-50 w-full">
                    <div className="flex justify-between items-start w-full">
                      <div className="flex-grow">
                        <h4 className="font-medium text-lg">{doc.name}</h4>
                        <div className="text-sm text-gray-600 mt-1">
                          <p>Pages: {doc.total_pages || 'N/A'}</p>
                          <p>Chunks: {doc.total_chunks || 'N/A'}</p>
                          <p>Chunking Method: {doc.chunking_method || 'N/A'}</p>
                          <p>Processing Date: {doc.timestamp ? new Date(doc.timestamp).toLocaleString() : 'N/A'}</p>
                        </div>
                      </div>
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => handleViewDocument(doc.name)}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(doc.name)}
                          className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8 w-full">
                  No chunked documents available
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6">
      <h1 className="text-blue-500 text-3xl font-bold text-center mb-6"> 检索增强生成工具 </h1>
      <hr />
      <h2 className="text-2xl font-bold mb-6">知识分块</h2>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            {/* 分块方法选择 */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">分块方法</label>
              <select
                value={chunkingOption}
                onChange={(e) => setChunkingOption(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="by_pages">按页面分块 (By Pages)</option>
                <option value="fixed_size">固定大小分块 (Fixed Size)</option>
                <option value="by_paragraphs">按段落分块 (By Paragraphs)</option>
                <option value="by_sentences">按句子分块 (By Sentences)</option>
                <option value="by_headings">按标题切分 (By Headings) - 需要结构化文档</option>
              </select>
            </div>

            {/* 根据分块方法显示不同的文档选择器 */}
            {chunkingOption === 'by_headings' ? (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">选择结构化文档</label>
                <select
                  value={selectedStructuredDoc}
                  onChange={(e) => setSelectedStructuredDoc(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  <option value="">请选择...</option>
                  {structuredDocuments.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.name}
                    </option>
                  ))}
                </select>
                {structuredDocuments.length === 0 && (
                  <p className="text-xs text-amber-600 mt-1">
                    暂无结构化文档，请先在「文件解析」页面使用结构化解析生成。
                  </p>
                )}
              </div>
            ) : (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">选择已加载的文档</label>
                <select
                  value={selectedDoc}
                  onChange={(e) => setSelectedDoc(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  <option value="">请选择...</option>
                  {loadedDocuments.map((doc) => (
                    <option key={doc.name} value={doc.name}>
                      {doc.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* 块大小（仅 fixed_size 和 by_headings 显示） */}
            {(chunkingOption === 'fixed_size' || chunkingOption === 'by_headings') && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">块大小（字符数）</label>
                <input
                  type="number"
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number(e.target.value))}
                  className="block w-full p-2 border rounded"
                  min="100"
                  max="5000"
                />
              </div>
            )}

            <button
              onClick={handleChunk}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
              disabled={
                (chunkingOption === 'by_headings' && !selectedStructuredDoc) ||
                (chunkingOption !== 'by_headings' && !selectedDoc)
              }
            >
              产生分块
            </button>
          </div>

          {status && (
            <div className={`p-4 rounded-lg ${
              status.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {status}
            </div>
          )}
          {processingStatus && (
            <div className="p-4 rounded-lg bg-blue-100 text-blue-700">
              {processingStatus}
            </div>
          )}
        </div>

        {/* Right Panel */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {renderRightPanel()}
        </div>
      </div>
    </div>
  );
};

export default ChunkFile;