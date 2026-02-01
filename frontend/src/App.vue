<template>
  <div class="app-container">
    <header class="app-header">
      <h1>🎓 奖学金材料验证系统</h1>
      <p>基于 AI 的申请材料自动化验证平台</p>
    </header>

    <main class="app-main">
      <!-- 文件上传区 -->
      <FileUpload 
        @files-selected="handleFilesSelected"
        @submit="handleSubmit"
        :uploading="uploading"
      />

      <!-- 提交历史列表 -->
      <div class="submissions-container" v-if="submissions.length > 0">
        <div class="history-header">
          <h2>验证历史</h2>
          <div class="header-buttons">
            <button class="clear-failed-button" @click="clearFailedRecords" title="清除失败的记录">
              ⚠️ 清除失败
            </button>
            <button class="clear-button" @click="clearHistory" title="清除所有历史记录">
              🗑️ 清除全部
            </button>
          </div>
        </div>
        <SubmissionCard
          v-for="submission in submissions"
          :key="submission.id"
          :submission="submission"
        />
      </div>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import FileUpload from './components/FileUpload.vue'
import SubmissionCard from './components/SubmissionCard.vue'
import { uploadFile, createSubmission, getSubmissionStatus, getSubmissionResults, getAllSubmissions } from './api/client.js'

export default {
  name: 'App',
  components: {
    FileUpload,
    SubmissionCard
  },
  setup() {
    const submissions = ref([])
    const uploading = ref(false)
    const activePolls = new Map()

    // 辅助函数：格式化时间为本地字符串
    const formatLocalTime = (isoString) => {
      if (!isoString) return ''
      // 修复: 如果是 ISO 格式且没有时区信息，默认为 UTC (添加 Z)
      let timeStr = isoString
      if (typeof isoString === 'string' && isoString.includes('T') && !isoString.endsWith('Z') && !isoString.includes('+')) {
        timeStr += 'Z'
      }
      return new Date(timeStr).toLocaleString()
    }

    // 辅助函数：将结果合并到文件列表中
    const mergeResultsToFiles = (files, results) => {
      // 🛡️ 防御性检查：确保 files 是数组
      if (!files) return []
      if (!Array.isArray(files)) return []
      
      if (!results || !Array.isArray(results) || results.length === 0) return files
      
      // 过滤掉空值或非对象，避免 results 中包含 null 导致报错
      const safeResults = results.filter(r => r && typeof r === 'object')
      
      return files.map(file => {
        if (!file) return null
        // 根据 file_id 找到对应的结果
        const resultItem = safeResults.find(r => r.file_id === file.file_id)
        if (resultItem) {
          // 合并属性，优先使用结果中的状态
          return {
             ...file,
             ...resultItem,
             status: resultItem.status || file.status
          }
        }
        return file
      }).filter(Boolean) // 过滤掉可能的 null
    }

    // 从后端加载历史记录
    const loadSubmissionsFromBackend = async () => {
      try {
        console.log('从后端加载历史记录...')
        const data = await getAllSubmissions(50)
        const safeList = Array.isArray(data) ? data : (data?.value || data?.items || [])
        submissions.value = safeList.filter(Boolean).map(sub => ({
          id: sub.id,
          // 关键修改1：如果有结果，合并到 files 中，确保页面能显示出已完成的状态
          files: mergeResultsToFiles(sub.files, sub.results),
          status: sub.status,
          progress: sub.progress,
          current_step: sub.current_step,
          // 关键修改2：转换时间格式
          created_at: formatLocalTime(sub.created_at),
          results: sub.results,
          error: sub.error
        }))
        console.log(`✅ 加载了 ${submissions.value.length} 条历史记录`)

        // 打印每个提交的状态和结果
        submissions.value.forEach(sub => {
          console.log(`  提交 ${sub.id.substring(0, 8)}: status=${sub.status}, hasResults=${!!sub.results}, resultsLength=${sub.results?.length || 0}`)
        })
      } catch (error) {
        console.error('加载历史记录失败:', error)
      }
    }

    // 停止轮询
    const stopPolling = (submissionId) => {
      if (activePolls.has(submissionId)) {
        clearTimeout(activePolls.get(submissionId))
        activePolls.delete(submissionId)
        console.log(`🛑 停止轮询: ${submissionId}`)
      }
    }

    // 轮询状态
    const pollSubmissionStatus = async (submissionId, attemptCount = 0) => {
      if (activePolls.has(submissionId)) {
        return
      }

      const submission = submissions.value.find(s => s.id === submissionId)
      if (!submission) return

      // 已有结果，不再轮询
      const hasResults = submission.results && Array.isArray(submission.results) && submission.results.length > 0
      if (hasResults) {
        console.log(`✅ 已有结果，跳过轮询: ${submissionId.substring(0, 8)}`)
        submission.status = 'completed'
        return
      }

      // 已经是最终状态
      if (['completed', 'failed', 'error'].includes(submission.status)) {
        stopPolling(submissionId)
        return
      }

      // 超时
      if (attemptCount >= 100) {
        submission.status = 'failed'
        submission.error = '验证超时'
        stopPolling(submissionId)
        return
      }

      try {
        const status = await getSubmissionStatus(submissionId)
        
        submission.status = status.status
        submission.progress = status.progress || 0
        submission.current_step = status.current_step || ''

        if (status.status === 'completed') {
          console.log(`✅ 验证完成: ${submissionId}`)
          const results = await getSubmissionResults(submissionId)
          submission.results = results.files
          stopPolling(submissionId)
        } else if (status.status === 'failed' || status.status === 'error') {
          console.log(`❌ 验证失败: ${submissionId}`)
          submission.error = status.error || '验证失败'
          stopPolling(submissionId)
        } else {
          // 继续轮询
          const timeoutId = setTimeout(() => {
            activePolls.delete(submissionId)
            pollSubmissionStatus(submissionId, attemptCount + 1)
          }, 3000)
          activePolls.set(submissionId, timeoutId)
        }
      } catch (error) {
        console.error(`轮询错误:`, error)
        
        if (error.message.includes('404')) {
          submission.status = 'failed'
          submission.error = '会话已过期'
          stopPolling(submissionId)
        } else {
          const timeoutId = setTimeout(() => {
            activePolls.delete(submissionId)
            pollSubmissionStatus(submissionId, attemptCount + 1)
          }, 3000)
          activePolls.set(submissionId, timeoutId)
        }
      }
    }

    const handleFilesSelected = (files) => {
      console.log('选择的文件:', files)
    }

    const handleSubmit = async (files) => {
      if (files.length === 0) {
        alert('请先选择文件')
        return
      }

      uploading.value = true

      try {
        // 1. 上传所有文件
        const uploadPromises = files.map(file => uploadFile(file))
        const uploadResults = await Promise.all(uploadPromises)
        
        const fileIds = uploadResults.map(result => result.file_id)
        
        // 2. 创建提交
        await createSubmission(fileIds)
        
        // 3. 添加到列表（从后端重新加载以获取完整数据）
        await loadSubmissionsFromBackend()
        
        // 4. 验证由 SubmissionCard 触发，避免重复调用
        
      } catch (error) {
        console.error('提交失败:', error)
        alert('提交失败: ' + error.message)
      } finally {
        uploading.value = false
      }
    }

    // 清除失败记录
    const clearFailedRecords = async () => {
      const failedCount = submissions.value.filter(s => s.status === 'failed').length
      if (failedCount === 0) {
        alert('没有失败的记录需要清除')
        return
      }
      
      if (confirm(`确定要清除 ${failedCount} 条失败记录吗？`)) {
        // 前端过滤（后端可以添加删除API）
        submissions.value = submissions.value.filter(s => s.status !== 'failed')
      }
    }

    // 清除所有历史
    const clearHistory = () => {
      if (confirm('确定要清除所有显示的历史记录吗？\n注意：这只会清除前端显示，后端数据库仍保留。')) {
        activePolls.forEach(clearTimeout)
        activePolls.clear()
        submissions.value = []
      }
    }

    // 页面加载时从后端加载数据
    onMounted(async () => {
      await loadSubmissionsFromBackend()
      
      // 恢复未完成任务的轮询
      submissions.value.forEach(sub => {
        // 只有当状态是 pending/processing 且没有结果时才轮询
        const hasResults = sub.results && Array.isArray(sub.results) && sub.results.length > 0
        const needsPoll = ['processing', 'pending'].includes(sub.status) && !hasResults
        
        console.log(`检查提交 ${sub.id.substring(0, 8)}: status=${sub.status}, hasResults=${hasResults}, needsPoll=${needsPoll}`)
        
        if (needsPoll) {
          console.log(`🔄 恢复轮询: ${sub.id}`)
          pollSubmissionStatus(sub.id)
        } else if (hasResults) {
          console.log(`✅ 已有结果，跳过轮询: ${sub.id}`)
          // 确保状态正确
          if (sub.status !== 'completed') {
            sub.status = 'completed'
          }
        }
      })
    })

    // 页面卸载时清理
    window.addEventListener('beforeunload', () => {
      activePolls.forEach(clearTimeout)
      activePolls.clear()
    })

    return {
      submissions,
      uploading,
      handleFilesSelected,
      handleSubmit,
      clearFailedRecords,
      clearHistory
    }
  }
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.app-header {
  text-align: center;
  color: white;
  margin-bottom: 40px;
}

.app-header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  font-weight: 700;
}

.app-header p {
  font-size: 1.1rem;
  opacity: 0.9;
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
}

.submissions-container {
  margin-top: 40px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.submissions-container h2 {
  color: white;
  font-size: 1.5rem;
  margin: 0;
}

.clear-failed-button,
.clear-button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.clear-failed-button:hover,
.clear-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.clear-failed-button {
  background: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.5);
}

.clear-failed-button:hover {
  background: rgba(255, 193, 7, 0.3);
}

</style>
