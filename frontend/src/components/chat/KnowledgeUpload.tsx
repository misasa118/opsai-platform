// src/components/chat/KnowledgeUpload.tsx
// 支持拖拽 / 点击上传 PDF/TXT/MD → 显示上传 / 处理进度 → 实时显示状态 的组件
// 对应后端：/api/v1/knowledge/upload /api/v1/knowledge/status/{fileId}
// ✅ 拖拽上传文件
// ✅ 点击选择文件
// ✅ 支持 PDF / TXT / MD
// ✅ 显示 上传中 → 向量化中 → 完成 → 失败
// ✅ 每 2 秒自动轮询后端状态
// ✅ 显示切块数量、错误信息
// ✅ 图标 + 颜色状态（蓝 / 橙 / 绿 / 红）
'use client'
import { useState, useRef, useCallback } from 'react'
import { Upload, FileText, CheckCircle, XCircle, Loader2, Trash2 } from 'lucide-react'
import { UploadedFile, UploadStatus } from '@/types/chat'
import { uploadFile, getFileStatus, listDocuments } from '@/lib/api'
import { clsx } from 'clsx'

// 状态管理 存放：文件名/fileId/状态（uploading /processing/ready /error)/错误信息/切块数量
export function KnowledgeUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const updateFileStatus = useCallback((fileId: string, updates: Partial<UploadedFile>) => {
    setFiles(prev => prev.map(f => f.fileId === fileId ? { ...f, ...updates } : f))
  }, [])

  // 轮询文件处理状态
  const pollStatus = useCallback(async (fileId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await getFileStatus(fileId)
        updateFileStatus(fileId, {
          status: data.status as UploadStatus,
          chunkCount: data.chunk_count,
          error: data.error,
        })
        if (data.status === 'ready' || data.status === 'error') {
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 2000)  // 每 2 秒查一次 轮询状态（每 2 秒查一次）
  }, [updateFileStatus])
  // 处理文件（核心函数）
  const processFile = useCallback(async (file: File) => {
    // 前端验证
    const allowed = ['.pdf', '.txt', '.md']
    const ext = '.' + file.name.split('.').pop()!.toLowerCase()
    if (!allowed.includes(ext)) {
      alert(`不支持的格式，仅支持: ${allowed.join(', ')}`)
      return
    }

    const newFile: UploadedFile = {
      fileId: '',
      filename: file.name,
      status: 'uploading',
    }
    setFiles(prev => [...prev, newFile])

    try {
      const { fileId } = await uploadFile(file)
      // 更新为真实的 fileId
      setFiles(prev => prev.map(f =>
        f.filename === file.name && f.fileId === ''
          ? { ...f, fileId, status: 'processing' }
          : f
      ))
      pollStatus(fileId)
    } catch (e: unknown) {
      setFiles(prev => prev.map(f =>
        f.filename === file.name && f.fileId === ''
          ? { ...f, status: 'error', error: e instanceof Error ? e.message : '上传失败' }
          : f
      ))
    }
  }, [pollStatus])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    droppedFiles.forEach(processFile)
  }, [processFile])

  const statusIcon = (status: UploadStatus) => {
    switch (status) {
      case 'uploading':   return <Loader2 className='h-4 w-4 animate-spin text-blue-500' />
      case 'processing':  return <Loader2 className='h-4 w-4 animate-spin text-orange-500' />
      case 'ready':       return <CheckCircle className='h-4 w-4 text-green-500' />
      case 'error':       return <XCircle className='h-4 w-4 text-red-500' />
      default:            return <FileText className='h-4 w-4 text-gray-400' />
    }
  }

  const statusText = (file: UploadedFile) => {
    switch (file.status) {
      case 'uploading':  return '上传中...'
      case 'processing': return 'AI 向量化中...'
      case 'ready':      return `已就绪（${file.chunkCount} 个片段）`
      case 'error':      return `失败: ${file.error}`
      default:           return ''
    }
  }

  return (
    <div className='space-y-3'>
      {/* 拖拽上传区域 */}
      <div
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setIsDragOver(true) }}
        onDragLeave={() => setIsDragOver(false)}
        onClick={() => fileInputRef.current?.click()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all',
          isDragOver
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
        )}
      >
        <Upload className='h-8 w-8 mx-auto mb-2 text-gray-400' />
        <p className='text-sm text-gray-600'>拖拽文件到这里，或点击选择</p>
        <p className='text-xs text-gray-400 mt-1'>支持 PDF、TXT、Markdown，最大 10MB</p>
        <input
          ref={fileInputRef}
          type='file'
          accept='.pdf,.txt,.md'
          multiple
          className='hidden'
          onChange={e => Array.from(e.target.files ?? []).forEach(processFile)}
        />
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div className='space-y-2'>
          {files.map((file, i) => (
            <div key={i} className='flex items-center gap-2 p-2 bg-gray-50 rounded-lg text-sm'>
              {statusIcon(file.status)}
              <span className='flex-1 truncate font-medium'>{file.filename}</span>
              <span className={clsx('text-xs',
                file.status === 'ready' ? 'text-green-600' :
                file.status === 'error' ? 'text-red-500' : 'text-gray-400'
              )}>
                {statusText(file)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}