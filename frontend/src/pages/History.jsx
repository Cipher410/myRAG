import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MarkdownViewer = ({ markdownText }) => {
  return (
    <div className="markdown-container">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdownText}</ReactMarkdown>
    </div>
  );
};

const History = () => {
  const [historyList, setHistoryList] = useState([]);
  const [selectedHistory, setSelectedHistory] = useState(null);

  // 从 localStorage 加载历史记录
  const loadHistory = () => {
    const stored = localStorage.getItem('chat_history');
    if (stored) {
      try {
        const list = JSON.parse(stored);
        list.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setHistoryList(list);
        // 如果有记录且未选中，默认选中第一条
        if (list.length > 0 && !selectedHistory) {
          setSelectedHistory(list[0]);
        }
      } catch (e) {
        console.error('解析历史记录失败', e);
        setHistoryList([]);
      }
    } else {
      setHistoryList([]);
      setSelectedHistory(null);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // 删除单条记录
  const deleteHistory = (id, e) => {
    e.stopPropagation();
    const newList = historyList.filter(item => item.id !== id);
    localStorage.setItem('chat_history', JSON.stringify(newList));
    setHistoryList(newList);
    // 如果删除的是当前选中的，清空选中或选第一条
    if (selectedHistory && selectedHistory.id === id) {
      setSelectedHistory(newList.length > 0 ? newList[0] : null);
    }
  };

  // 清空所有记录
  const clearAll = () => {
    if (window.confirm('确定要清空所有历史对话吗？')) {
      localStorage.removeItem('chat_history');
      setHistoryList([]);
      setSelectedHistory(null);
    }
  };

  // 格式化时间显示
  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">历史对话记录</h1>
        {historyList.length > 0 && (
          <button
            onClick={clearAll}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            清空所有
          </button>
        )}
      </div>

      {historyList.length === 0 ? (
        <div className="text-center text-gray-500 mt-10">
          暂无历史对话，请先在“响应生成”页面生成回答。
        </div>
      ) : (
        <div className="flex flex-1 gap-6 min-h-0">
          {/* 左侧列表 */}
          <div className="w-1/3 border rounded-lg bg-white shadow-sm overflow-y-auto">
            <div className="divide-y divide-gray-200">
              {historyList.map((record) => (
                <div
                  key={record.id}
                  onClick={() => setSelectedHistory(record)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                    selectedHistory && selectedHistory.id === record.id
                      ? 'bg-blue-50 border-l-4 border-blue-500'
                      : ''
                  }`}
                >
                  <div className="font-medium text-gray-900 mb-1 truncate">
                    问题：{record.query.substring(0, 80)}
                    {record.query.length > 80 ? '...' : ''}
                  </div>
                  <div className="text-sm text-gray-500 mb-1">
                    模型：{record.provider} / {record.modelName}
                  </div>
                  <div className="text-xs text-gray-400 flex justify-between items-center">
                    <span>{formatDate(record.timestamp)}</span>
                    <button
                      onClick={(e) => deleteHistory(record.id, e)}
                      className="text-red-500 hover:text-red-700 text-sm"
                      title="删除"
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 右侧详情 */}
          <div className="w-2/3 border rounded-lg bg-white shadow-sm overflow-y-auto p-4">
            {selectedHistory ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-700 mb-2">提问</h3>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="whitespace-pre-wrap">{selectedHistory.query}</p>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-700 mb-2">生成的回答</h3>
                  <div className="p-3 bg-gray-50 rounded-lg max-h-[500px] overflow-y-auto">
                    <MarkdownViewer markdownText={selectedHistory.response} />
                  </div>
                </div>
                {selectedHistory.searchResults && selectedHistory.searchResults.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-700 mb-2">检索上下文（共{selectedHistory.searchResults.length}条）</h3>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {selectedHistory.searchResults.map((result, idx) => (
                        <div key={idx} className="p-2 bg-gray-50 rounded border-l-4 border-blue-300">
                          <div className="text-xs text-gray-500 mb-1">
                            相关度：{(result.score * 100).toFixed(1)}% | 来源：{result.metadata?.source || '未知'} | 页码：{result.metadata?.page || '?'}
                          </div>
                          <p className="text-sm whitespace-pre-wrap">{result.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="text-xs text-gray-400 text-right pt-2 border-t">
                  生成时间：{formatDate(selectedHistory.timestamp)} | 模型：{selectedHistory.provider} / {selectedHistory.modelName}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                请从左侧选择一条历史记录
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default History;