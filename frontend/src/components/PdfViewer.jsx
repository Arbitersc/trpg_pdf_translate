import React, { useState, useEffect, useRef } from 'react'
import * as pdfjsLib from 'pdfjs-dist'
import './PdfViewer.css'

// 配置PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`

function PdfViewer({ filename, uploadedFile, apiUrl, onFileUpload }) {
  const [pdfDoc, setPdfDoc] = useState(null)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [pageCanvases, setPageCanvases] = useState([])
  const containerRef = useRef(null)
  const fileInputRef = useRef(null)
  const renderedPagesRef = useRef(new Set())
  const renderingRef = useRef(new Set())

  useEffect(() => {
    if (filename) {
      loadPdfFromApi()
    } else if (uploadedFile) {
      loadPdfFromFile(uploadedFile)
    }

    // 清理函数
    return () => {
      renderedPagesRef.current.clear()
      renderingRef.current.clear()
      setPageCanvases([])
    }
  }, [filename, uploadedFile])

  // 当PDF加载完成后，初始化canvas数组
  useEffect(() => {
    if (pdfDoc && totalPages > 0) {
      const canvases = Array(totalPages).fill(null).map((_, index) => ({
        pageNum: index + 1,
        canvasRef: React.createRef(),
        loaded: false
      }))
      setPageCanvases(canvases)
    }
  }, [pdfDoc, totalPages])

  const loadPdfFromApi = async () => {
    setLoading(true)
    setError('')
    renderedPagesRef.current.clear()
    renderingRef.current.clear()

    try {
      const pdfUrl = `${apiUrl}/${filename}`
      const loadingTask = pdfjsLib.getDocument(pdfUrl)
      const pdf = await loadingTask.promise

      setPdfDoc(pdf)
      setTotalPages(pdf.numPages)
    } catch (err) {
      console.error('加载PDF错误:', err)
      setError(`加载PDF失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const loadPdfFromFile = async (file) => {
    setLoading(true)
    setError('')
    renderedPagesRef.current.clear()
    renderingRef.current.clear()

    try {
      const fileReader = new FileReader()
      fileReader.onload = async (e) => {
        const typedArray = new Uint8Array(e.target.result)
        const loadingTask = pdfjsLib.getDocument(typedArray)
        const pdf = await loadingTask.promise

        setPdfDoc(pdf)
        setTotalPages(pdf.numPages)
        setLoading(false)
      }
      fileReader.onerror = () => {
        setError('读取文件失败')
        setLoading(false)
      }
      fileReader.readAsArrayBuffer(file)
    } catch (err) {
      console.error('加载PDF错误:', err)
      setError(`加载PDF失败: ${err.message}`)
      setLoading(false)
    }
  }

  // 渲染单个页面
  const renderPage = async (pageNum, canvas) => {
    if (!pdfDoc || !canvas || renderedPagesRef.current.has(pageNum) || renderingRef.current.has(pageNum)) {
      return
    }

    renderingRef.current.add(pageNum)

    try {
      const page = await pdfDoc.getPage(pageNum)
      const ctx = canvas.getContext('2d')

      // 计算缩放比例以适应容器宽度
      const containerWidth = containerRef.current ? containerRef.current.clientWidth - 40 : 800
      const viewportRaw = page.getViewport({ scale: 1.0 })
      const scale = containerWidth / viewportRaw.width
      const viewport = page.getViewport({ scale: Math.min(scale, 2.0) })

      // 设置canvas尺寸
      canvas.height = viewport.height
      canvas.width = viewport.width

      // 渲染PDF页面
      const renderContext = {
        canvasContext: ctx,
        viewport: viewport
      }

      await page.render(renderContext).promise
      renderedPagesRef.current.add(pageNum)
    } catch (err) {
      console.error('渲染页面错误:', err)
      setError(`渲染页面失败: ${err.message}`)
    } finally {
      renderingRef.current.delete(pageNum)
    }
  }

  // 初始化渲染前几页
  useEffect(() => {
    if (pageCanvases.length > 0 && pdfDoc) {
      // 首先渲染前3页
      const pagesToRender = Math.min(3, pageCanvases.length)
      for (let i = 0; i < pagesToRender; i++) {
        const pageData = pageCanvases[i]
        if (pageData && pageData.canvasRef.current && !renderedPagesRef.current.has(pageData.pageNum)) {
          renderPage(pageData.pageNum, pageData.canvasRef.current)
        }
      }
    }
  }, [pageCanvases, pdfDoc])

  // 监听滚动事件，实现懒加载
  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current || pageCanvases.length === 0) return

      const container = containerRef.current
      const containerRect = container.getBoundingClientRect()
      const containerTop = containerRect.top
      const containerBottom = containerRect.bottom

      // 找到所有可见的canvas
      pageCanvases.forEach((pageData) => {
        if (pageData.canvasRef.current) {
          const canvas = pageData.canvasRef.current
          const canvasRect = canvas.getBoundingClientRect()

          // 检查canvas是否在视口内
          const isVisible = canvasRect.bottom >= containerTop && canvasRect.top <= containerBottom

          if (isVisible && !renderedPagesRef.current.has(pageData.pageNum)) {
            renderPage(pageData.pageNum, canvas)
          }
        }
      })
    }

    const container = containerRef.current
    if (container) {
      container.addEventListener('scroll', handleScroll)
      // 初始调用一次
      handleScroll()

      return () => {
        container.removeEventListener('scroll', handleScroll)
      }
    }
  }, [pageCanvases, pdfDoc])

  const handleDragEnter = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      const file = files[0]
      if (file.type === 'application/pdf') {
        if (onFileUpload) {
          onFileUpload(file)
        }
      } else {
        setError('请上传PDF文件')
      }
    }
  }

  const handleFileSelect = (e) => {
    const files = e.target.files
    if (files && files.length > 0) {
      const file = files[0]
      if (file.type === 'application/pdf') {
        if (onFileUpload) {
          onFileUpload(file)
        }
      } else {
        setError('请上传PDF文件')
      }
    }
  }

  const handleClick = () => {
    if (!pdfDoc && !loading) {
      fileInputRef.current?.click()
    }
  }

  // 如果没有PDF文件，显示拖拽上传区域
  if (!pdfDoc && !loading) {
    return (
      <div className="pdf-viewer">
        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <div className="upload-content">
            <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <polyline points="17 8 12 3 7 8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <line x1="12" y1="3" x2="12" y2="15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <p className="upload-text">拖拽PDF文件到此处</p>
            <p className="upload-subtext">或点击选择文件</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>
        {error && <div className="error">{error}</div>}
      </div>
    )
  }

  return (
    <div className="pdf-viewer">
      {pdfDoc && (
        <>
          <div className="viewer-controls">
            <div className="page-info">
              共 {totalPages} 页
            </div>
          </div>

          {loading && <div className="loading">加载中...</div>}

          {error && <div className="error">{error}</div>}

          <div className="canvas-container" ref={containerRef}>
            {pageCanvases.map((pageData, index) => (
              <div key={pageData.pageNum} className="page-wrapper">
                <div className="page-number">第 {pageData.pageNum} 页</div>
                <canvas
                  ref={pageData.canvasRef}
                  className="pdf-page-canvas"
                />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export default PdfViewer
