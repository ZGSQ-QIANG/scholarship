<!-- filepath: e:\scholarship\frontend\src\components\SubmissionCard.vue -->
<template>
  <div class="submission-card">
    <div class="submission-header" @click="toggleExpanded">
      <div class="header-left">
        <span class="status-badge" :class="statusClass">{{ statusText }}</span>
        <span class="submission-time">{{ formatTime(submission.created_at) }}</span>
        <span class="file-count">{{ submission.files.length }} 个文件</span>
      </div>
      <div class="header-right">
        <span class="expand-icon">{{ expanded ? '▼' : '▶' }}</span>
      </div>
    </div>

    <div v-if="expanded" class="submission-content">
      <!-- 总体进度条 -->
      <div v-if="status.status === 'processing'" class="progress-section">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: status.progress + '%' }"></div>
        </div>
        <p class="progress-text">{{ status.current_step }} ({{ status.progress }}%)</p>
      </div>

      <!-- 总体错误提示 -->
      <div v-if="status.status === 'failed'" class="error-section">
        <div class="error-banner">
          <span class="error-icon">⚠️</span>
          <div class="error-content">
            <h4>验证失败</h4>
            <p>{{ status.current_step }}</p>
            <details v-if="status.error" class="error-details">
              <summary>查看详细错误</summary>
              <pre>{{ status.error }}</pre>
            </details>
          </div>
        </div>
        <button class="retry-button" @click="retryVerification">
          🔄 重试验证
        </button>
      </div>

      <!-- 文件列表 - 始终显示 -->
      <div class="files-section">
        <div 
          v-for="(file, index) in submission.files" 
          :key="file.id || file.file_id || index"
          class="file-item"
        >
          <!-- 如果有结果，显示 ResultCard -->
          <div v-if="getFileResult(file.id || file.file_id)">
            <ResultCard :result="getFileResult(file.id || file.file_id)" />
            
            <!-- 如果验证失败，显示重新上传按钮 -->
            <div v-if="isFileFailed(file.id || file.file_id)" class="retry-file-section">
              <button class="retry-file-button" @click="retryFile(file.id || file.file_id, file.filename)">
                🔄 重新上传此文件
              </button>
              <input 
                type="file" 
                :ref="el => fileInputRefs[file.id || file.file_id] = el"
                style="display: none"
                @change="handleFileReupload($event, file.id || file.file_id)"
              />
            </div>
          </div>
          
          <!-- 否则显示文件状态卡片 -->
          <div v-else class="file-status-card">
            <div class="file-header">
              <span class="file-icon">📄</span>
              <span class="file-name">{{ file.filename || file.name || '未知文件' }}</span>
              <span class="file-status-badge" :class="getFileStatusClass(index)">
                {{ getFileStatusText(index) }}
              </span>
            </div>
            
            <!-- 如果正在处理这个文件 -->
            <div v-if="isProcessingFile(index)" class="file-progress">
              <div class="mini-progress-bar">
                <div class="mini-progress-fill"></div>
              </div>
              <p class="file-progress-text">{{ getCurrentFileStep(index) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 调试信息（开发时使用，生产环境删除） -->
      <details class="debug-info" style="margin-top: 20px; padding: 10px; background: #f3f4f6; border-radius: 4px;">
        <summary style="cursor: pointer; font-weight: bold;">🐛 调试信息</summary>
        <pre style="margin-top: 10px; font-size: 12px; overflow-x: auto;">
Submission: {{ JSON.stringify(submission, null, 2) }}

Status: {{ JSON.stringify(status, null, 2) }}

Results: {{ JSON.stringify(results, null, 2) }}
        </pre>
      </details>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import ResultCard from './ResultCard.vue';
import { verifySubmission, getSubmissionStatus, getSubmissionResults } from '../api/client.js';

export default {
  name: 'SubmissionCard',
  components: { ResultCard },
  props: {
    submission: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const expanded = ref(true);
    const status = ref({
      status: 'pending',
      progress: 0,
      current_step: '等待开始...',
      error: null
    });
    const results = ref(null);
    const isVerifying = ref(false);
    const fileInputRefs = ref({});
    let pollInterval = null;

    // 打印 submission 数据结构
    console.log('Submission data:', props.submission);

    const statusClass = computed(() => {
      const statusMap = {
        pending: 'status-pending',
        processing: 'status-processing',
        completed: 'status-success',
        failed: 'status-error'
      };
      return statusMap[status.value.status] || 'status-pending';
    });

    const statusText = computed(() => {
      const textMap = {
        pending: '⏳ 等待中',
        processing: '⚙️ 处理中',
        completed: '✅ 已完成',
        failed: '❌ 失败'
      };
      return textMap[status.value.status] || '未知';
    });

    const toggleExpanded = () => {
      expanded.value = !expanded.value;
    };

    const formatTime = (isoString) => {
      if (!isoString) return '';
      // 如果没有时区标识，且看起来是 ISO 格式，添加 Z 当作 UTC 处理
      // 解决后端返回 UTC 时间但未带时区信息导致显示为本地时间的问题
      let timeStr = isoString;
      if (isoString.includes('T') && !isoString.endsWith('Z') && !isoString.includes('+')) {
        timeStr += 'Z';
      }
      const date = new Date(timeStr);
      return date.toLocaleString('zh-CN');
    };

    // 获取文件结果
    const getFileResult = (fileId) => {
      // 1. 尝试从 polling 到的 results 中查找
      if (results.value && results.value.files) {
        const result = results.value.files.find(f => f.file_id === fileId);
        if (result) {
          // console.log(`getFileResult match in results: ${fileId}`);
          return result;
        }
      }
      
      // 2. 尝试从 submission.files 中查找 (如果 App.vue 已经合并了结果)
      if (props.submission.files) {
        const file = props.submission.files.find(f => (f.id === fileId || f.file_id === fileId));
        
        // 检查是否有结果特征 (已合并结果的文件对象)
        if (file && (file.verification_status || file.ai_conclusion || file.tool_results)) {
          // console.log(`getFileResult match in files (merged): ${fileId}`);
          return file;
        }
        
        // 如果 status 是 success/failed 且有 result 对象 (嵌套结构)
        if (file && (file.status === 'success' || file.status === 'completed') && file.result) {
           return {
             ...file,
             ...file.result
           };
        }
      }
      
      // console.log(`getFileResult no match: ${fileId}`);
      return null;
    };

    // 判断文件是否正在处理
    const isProcessingFile = (fileIndex) => {
      if (status.value.status !== 'processing') return false;
      const totalFiles = props.submission.files.length;
      const currentFileIndex = Math.floor((status.value.progress / 100) * totalFiles);
      return fileIndex === currentFileIndex;
    };

    // 获取文件状态类
    const getFileStatusClass = (fileIndex) => {
      const file = props.submission.files[fileIndex];
      if (!file) return 'file-pending';
      
      const result = getFileResult(file.id || file.file_id);
      if (result) {
        return 'file-completed';
      }
      if (isProcessingFile(fileIndex)) {
        return 'file-processing';
      }
      if (status.value.status === 'failed') {
        return 'file-error';
      }
      return 'file-pending';
    };

    // 获取文件状态文本
    const getFileStatusText = (fileIndex) => {
      const file = props.submission.files[fileIndex];
      if (!file) return '未知';
      
      const result = getFileResult(file.id || file.file_id);
      if (result) {
        return '✅ 已完成';
      }
      if (isProcessingFile(fileIndex)) {
        return '⚙️ 处理中';
      }
      if (status.value.status === 'failed') {
        return '❌ 失败';
      }
      return '⏳ 等待中';
    };

    // 获取当前文件处理步骤
    const getCurrentFileStep = (fileIndex) => {
      if (isProcessingFile(fileIndex)) {
        return status.value.current_step;
      }
      return '';
    };

    const startVerification = async () => {
      if (isVerifying.value) {
        console.log('验证已在进行中，跳过');
        return;
      }

      isVerifying.value = true;

      try {
        const response = await verifySubmission(props.submission.id);
        console.log('Verify response:', response);
        startPolling();
      } catch (error) {
        console.error('启动验证失败:', error);
        status.value = {
          status: 'failed',
          progress: 0,
          current_step: '启动验证失败',
          error: error.message || '未知错误'
        };
        isVerifying.value = false;
      }
    };

    const startPolling = () => {
      if (pollInterval) {
        console.log('已有轮询在运行，跳过');
        return;
      }

      console.log(`开始轮询 submission ${props.submission.id}`);
      
      pollInterval = setInterval(async () => {
        try {
          const statusData = await getSubmissionStatus(props.submission.id);
          console.log('Status data:', statusData);
          status.value = statusData;

          if (statusData.status === 'completed') {
            console.log('验证完成，获取结果并停止轮询');
            const resultsData = await getSubmissionResults(props.submission.id);
            console.log('Results data:', resultsData);
            results.value = resultsData;
            stopPolling();
            isVerifying.value = false;
          } else if (statusData.status === 'failed') {
            console.log('验证失败，停止轮询');
            stopPolling();
            isVerifying.value = false;
          }
        } catch (error) {
          console.error('获取状态失败:', error);
          if (error.response?.status === 404) {
            console.log('任务不存在，停止轮询');
            stopPolling();
            isVerifying.value = false;
          }
        }
      }, 2000);
    };

    const stopPolling = () => {
      if (pollInterval) {
        console.log(`停止轮询 submission ${props.submission.id}`);
        clearInterval(pollInterval);
        pollInterval = null;
      }
    };

    const retryVerification = () => {
      if (isVerifying.value) {
        console.log('验证正在进行中，无法重试');
        return;
      }

      status.value = {
        status: 'pending',
        progress: 0,
        current_step: '准备重试...',
        error: null
      };
      results.value = null;
      startVerification();
    };
    
    // 判断文件是否失败
    const isFileFailed = (fileId) => {
      const result = getFileResult(fileId);
      if (!result) return false;
      return result.status === 'error' || result.status === 'failed';
    };
    
    // 点击重新上传文件按钮
    const retryFile = (fileId, filename) => {
      console.log(`重新上传文件: ${filename} (${fileId})`);
      const input = fileInputRefs.value[fileId];
      if (input) {
        input.click();
      }
    };
    
    // 处理文件重新上传
    const handleFileReupload = async (event, oldFileId) => {
      const file = event.target.files[0];
      if (!file) return;
      
      try {
        console.log(`上传新文件替换 ${oldFileId}:`, file.name);
        
        // 导入 uploadFile 函数
        const { uploadFile, replaceSubmissionFile, verifySubmissionFile } = await import('../api/client.js');
        
        // 上传新文件
        const uploadResult = await uploadFile(file);
        console.log('上传成功:', uploadResult);
        
        // 通知后端替换提交里的文件，并重置状态
        const replaceResult = await replaceSubmissionFile(
          props.submission.id,
          oldFileId,
          uploadResult.file_id,
          uploadResult.filename
        );
        console.log('替换成功:', replaceResult);
        
        // 同步更新前端提交数据
        if (replaceResult && Array.isArray(replaceResult.files)) {
          props.submission.files = replaceResult.files;
        }
        if (Array.isArray(props.submission.results)) {
          props.submission.results = props.submission.results.filter(r => r.file_id !== oldFileId);
        }
        props.submission.status = 'pending';
        props.submission.current_step = '等待验证...';
        
        // 更新提交中的文件ID
        const fileIndex = props.submission.files.findIndex(f => 
          (f.id || f.file_id) === oldFileId
        );
        
        if (fileIndex !== -1) {
          props.submission.files[fileIndex] = {
            ...props.submission.files[fileIndex],
            id: uploadResult.file_id,
            file_id: uploadResult.file_id,
            filename: uploadResult.filename
          };
        }
        
        // 清除旧结果
        if (results.value && results.value.files) {
          results.value.files = results.value.files.filter(f => f.file_id !== oldFileId);
        }
        
        // 重新开始验证（仅该文件）
        status.value = {
          status: 'pending',
          progress: 0,
          current_step: '准备验证新文件...',
          error: null
        };
        
        await verifySubmissionFile(props.submission.id, uploadResult.file_id);
        startPolling();
        
      } catch (error) {
        console.error('重新上传文件失败:', error);
        alert('重新上传失败: ' + error.message);
      }
      
      // 清空 input
      event.target.value = '';
    };

    onMounted(() => {
      console.log(`SubmissionCard mounted: ${props.submission.id}`);
      
      // 🔑 关键修复：只有当提交是全新的（没有 results）且状态是 pending 时才开始验证
      const hasResults = props.submission.results && 
                         Array.isArray(props.submission.results) && 
                         props.submission.results.length > 0;
      
      const isNewSubmission = props.submission.status === 'pending' && !hasResults;
      
      console.log(`  hasResults: ${hasResults}, isNewSubmission: ${isNewSubmission}`);
      
      if (isNewSubmission) {
        console.log(`  → 开始新的验证流程`);
        startVerification();
      } else if (hasResults) {
        console.log(`  → 已有结果，直接显示`);
        // 直接使用现有结果
        results.value = {
          files: props.submission.results
        };
        status.value = {
          status: 'completed',
          progress: 100,
          current_step: '验证完成'
        };
      } else if (props.submission.status === 'processing') {
        console.log(`  → 恢复进行中的验证`);
        startPolling();
      }
    });

    onUnmounted(() => {
      console.log(`SubmissionCard unmounted: ${props.submission.id}`);
      stopPolling();
    });

    return {
      expanded,
      status,
      results,
      statusClass,
      statusText,
      toggleExpanded,
      formatTime,
      retryVerification,
      getFileResult,
      isProcessingFile,
      getFileStatusClass,
      getFileStatusText,
      getCurrentFileStep,
      isFileFailed,
      retryFile,
      handleFileReupload,
      fileInputRefs
    };
  }
};
</script>

<style scoped>
.submission-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.submission-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.submission-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
}

.status-pending {
  background: rgba(255, 255, 255, 0.3);
}

.status-processing {
  background: rgba(59, 130, 246, 0.3);
  animation: pulse 2s infinite;
}

.status-success {
  background: rgba(34, 197, 94, 0.3);
}

.status-error {
  background: rgba(239, 68, 68, 0.3);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.submission-time {
  font-size: 14px;
  opacity: 0.9;
}

.file-count {
  font-size: 14px;
  opacity: 0.9;
}

.expand-icon {
  font-size: 14px;
  transition: transform 0.3s ease;
}

.submission-content {
  padding: 20px;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  color: #6b7280;
  font-size: 14px;
}

/* 错误样式 */
.error-section {
  margin-bottom: 20px;
}

.error-banner {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  margin-bottom: 12px;
}

.error-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.error-content {
  flex: 1;
}

.error-content h4 {
  margin: 0 0 8px 0;
  color: #dc2626;
  font-size: 16px;
}

.error-content p {
  margin: 0 0 8px 0;
  color: #991b1b;
  font-size: 14px;
}

.error-details {
  margin-top: 8px;
}

.error-details summary {
  cursor: pointer;
  color: #dc2626;
  font-size: 13px;
  user-select: none;
}

.error-details summary:hover {
  text-decoration: underline;
}

.error-details pre {
  margin-top: 8px;
  padding: 12px;
  background: white;
  border: 1px solid #fecaca;
  border-radius: 4px;
  font-size: 12px;
  color: #991b1b;
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.retry-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.retry-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.retry-button:active {
  transform: translateY(0);
}

/* 文件列表样式 */
.files-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  width: 100%;
}

/* 文件状态卡片 */
.file-status-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;
}

.file-status-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.file-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}

.file-pending {
  background: #f3f4f6;
  color: #6b7280;
}

.file-processing {
  background: #dbeafe;
  color: #1e40af;
  animation: pulse 2s infinite;
}

.file-completed {
  background: #d1fae5;
  color: #065f46;
}

/* 文件进度 */
.file-progress {
  margin-top: 12px;
}

.mini-progress-bar {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 6px;
}

.mini-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  animation: progressAnimation 1.5s ease-in-out infinite;
}

@keyframes progressAnimation {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 100%; }
}

.file-progress-text {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.retry-file-section {
  margin-top: 10px;
  padding: 10px;
  background: rgba(239, 68, 68, 0.05);
  border-radius: 8px;
  text-align: center;
}

.retry-file-button {
  background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
}

.retry-file-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.retry-file-button:active {
  transform: translateY(0);
}

.pending-section {
  text-align: center;
  padding: 40px 20px;
  color: #6b7280;
  font-size: 16px;
}
</style>
