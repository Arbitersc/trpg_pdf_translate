import React, { useState, useEffect } from 'react'
import PdfViewer from './components/PdfViewer'
import PdfManager from './components/PdfManager'
import TerminologyViewer from './components/TerminologyViewer'
import './App.css'

function App() {
  const [pdfList, setPdfList] = useState([])
  const [selectedPdf, setSelectedPdf] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadedPdf, setUploadedPdf] = useState(null)
  const [currentView, setCurrentView] = useState('pdf') // 'pdf', 'pdf-manage', 'terminology'

  // 加载PDF文件列表
  useEffect(() => {
    fetchPdfList()
  }, [])

  const fetchPdfList = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/pdfs')
      const data = await response.json()

      if (data.success) {
        setPdfList(data.files)
      } else {
        setError('加载PDF列表失败')
      }
    } catch (err) {
      console.error('加载PDF列表错误:', err)
      setError('无法连接到后端服务，请确保后端服务已启动')
    } finally {
      setLoading(false)
    }
  }

  const handlePdfSelect = (filename) => {
    setSelectedPdf(filename)
  }

  const handlePdfUpload = (file) => {
    setUploadedPdf(file)
  }

  return (
    <div className="App">
      <div className="main-layout">
        {currentView === 'pdf' ? (
          <>
            {/* PDF阅读区域 - 47%宽度 */}
            <div className="content-area pdf-area">
              <div className="content-header">
                <h2>PDF 阅读器</h2>
              </div>
              <PdfViewer
                filename={selectedPdf}
                uploadedFile={uploadedPdf}
                apiUrl="http://localhost:5000/api/pdf"
                onFileUpload={handlePdfUpload}
              />
            </div>

            {/* 文档展示区域 - 47%宽度 */}
            <div className="content-area document-area">
              <div className="content-header">
                <h2>文档展示</h2>
              </div>
              <div className="document-content">
                <p className="placeholder-text">文档内容将显示在这里</p>
              </div>
            </div>
          </>
        ) : currentView === 'pdf-manage' ? (
          <>
            {/* PDF管理界面 - 占据整个主内容区 */}
            <div className="content-area full-width">
              <div className="content-header">
                <h2>PDF 管理</h2>
              </div>
              <PdfManager
                pdfList={pdfList}
                selectedPdf={selectedPdf}
                onPdfSelect={handlePdfSelect}
                loading={loading}
                error={error}
                onFileUpload={handlePdfUpload}
              />
            </div>
          </>
        ) : (
          <>
            {/* 术语库界面 - 占据整个主内容区 */}
            <div className="content-area full-width">
              <div className="content-header">
                <h2>术语库</h2>
              </div>
              <TerminologyViewer />
            </div>
          </>
        )}

        {/* 右侧导航栏 */}
        <div className="right-sidebar">
          <div className="nav-button-group">
            <button
              className={`nav-button ${currentView === 'pdf' ? 'active' : ''}`}
              onClick={() => setCurrentView('pdf')}
              title="PDF 显示"
            >
              <div className="nav-button-content">
                <img src="./resource/pdf.svg" alt="PDF" className="nav-icon" />
                <span className="nav-text">PDF 显示</span>
              </div>
            </button>

            <button
              className={`nav-button ${currentView === 'pdf-manage' ? 'active' : ''}`}
              onClick={() => setCurrentView('pdf-manage')}
              title="PDF 管理"
            >
              <div className="nav-button-content">
                <img src="./resource/manage.svg" alt="PDF 管理" className="nav-icon" />
                <span className="nav-text">PDF 管理</span>
              </div>
            </button>

            <button
              className={`nav-button ${currentView === 'terminology' ? 'active' : ''}`}
              onClick={() => setCurrentView('terminology')}
              title="术语库"
            >
              <div className="nav-button-content">
                <img src="./resource/dictionary.svg" alt="术语库" className="nav-icon" />
                <span className="nav-text">术语库</span>
              </div>
            </button>
          </div>
        </div>
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

export default App
