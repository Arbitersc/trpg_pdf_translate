import React from 'react'
import './PdfManager.css'

function PdfManager({ pdfList, selectedPdf, onPdfSelect, loading, error, onFileUpload }) {
  const handleFileChange = (e) => {
    const files = e.target.files
    if (files && files.length > 0) {
      const file = files[0]
      if (file.type === 'application/pdf') {
        onFileUpload(file)
      } else {
        alert('请上传PDF文件')
      }
    }
  }

  return (
    <div className="pdf-manager">
      <div className="manager-content">
        {/* 上传区域 */}
        <div className="upload-section">
          <div className="upload-box">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="file-input"
              id="pdf-upload"
            />
            <label htmlFor="pdf-upload" className="upload-label">
              <div className="upload-icon">📁</div>
              <div className="upload-text">点击上传PDF文件</div>
            </label>
          </div>
        </div>

        {/* PDF文件列表 */}
        <div className="pdf-list-section">
          <h3 className="list-title">PDF文件列表</h3>

          {loading && <div className="loading">加载中...</div>}

          {error && <div className="error">{error}</div>}

          {!loading && !error && (
            <div className="pdf-list">
              {pdfList.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📭</div>
                  <p>暂无PDF文件</p>
                  <p className="empty-hint">请上传PDF文件开始使用</p>
                </div>
              ) : (
                pdfList.map((file) => (
                  <div
                    key={file.filename}
                    className={`pdf-item ${selectedPdf === file.filename ? 'selected' : ''}`}
                    onClick={() => onPdfSelect(file.filename)}
                  >
                    <div className="pdf-item-icon">📄</div>
                    <div className="pdf-item-info">
                      <div className="pdf-item-name">{file.filename}</div>
                      <div className="pdf-item-size">{formatFileSize(file.size)}</div>
                    </div>
                    {selectedPdf === file.filename && (
                      <div className="pdf-item-check">✓</div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* 当前选择的文件 */}
        {selectedPdf && (
          <div className="current-selection">
            <h3 className="selection-title">当前选择</h3>
            <div className="selection-info">
              <div className="selection-icon">📖</div>
              <div className="selection-details">
                <div className="selection-name">{selectedPdf}</div>
                <div className="selection-status">已加载，可以开始阅读</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

export default PdfManager
