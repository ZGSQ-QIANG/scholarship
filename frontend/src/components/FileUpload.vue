<template>
  <div class="file-upload-container">
    <div 
      class="upload-area"
      :class="{ 'dragging': isDragging }"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input 
        ref="fileInput"
        type="file" 
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.bmp,.webp"
        @change="handleFileSelect"
        style="display: none;"
      />
      
      <div class="upload-icon">📁</div>
      <h3>拖拽文件到此处，或点击选择文件</h3>
      <p>支持 PDF、PNG、JPG、JPEG、BMP、WEBP 格式</p>
    </div>

    <!-- 文件列表 -->
    <div v-if="selectedFiles.length > 0" class="file-list">
      <h4>已选择 {{ selectedFiles.length }} 个文件：</h4>
      <div class="file-item" v-for="(file, index) in selectedFiles" :key="index">
        <span class="file-name">📄 {{ file.name }}</span>
        <span class="file-size">{{ formatFileSize(file.size) }}</span>
        <button class="remove-btn" @click="removeFile(index)">✕</button>
      </div>
      
      <div class="action-buttons">
        <button class="clear-btn" @click="clearFiles">清空</button>
        <button 
          class="submit-btn" 
          @click="submitFiles"
          :disabled="uploading"
        >
          {{ uploading ? '上传中...' : '开始验证' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'FileUpload',
  props: {
    uploading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['files-selected', 'submit'],
  setup(props, { emit }) {
    const selectedFiles = ref([])
    const isDragging = ref(false)
    const fileInput = ref(null)

    const handleDragOver = () => {
      isDragging.value = true
    }

    const handleDragLeave = () => {
      isDragging.value = false
    }

    const handleDrop = (e) => {
      isDragging.value = false
      const files = Array.from(e.dataTransfer.files)
      addFiles(files)
    }

    const triggerFileInput = () => {
      fileInput.value.click()
    }

    const handleFileSelect = (e) => {
      const files = Array.from(e.target.files)
      addFiles(files)
    }

    const addFiles = (files) => {
      // 验证文件类型
      const allowedTypes = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.webp']
      const validFiles = files.filter(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase()
        return allowedTypes.includes(ext)
      })

      if (validFiles.length !== files.length) {
        alert('部分文件格式不支持，已自动过滤')
      }

      selectedFiles.value.push(...validFiles)
      emit('files-selected', selectedFiles.value)
    }

    const removeFile = (index) => {
      selectedFiles.value.splice(index, 1)
    }

    const clearFiles = () => {
      selectedFiles.value = []
    }

    const submitFiles = () => {
      emit('submit', selectedFiles.value)
      selectedFiles.value = []
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    return {
      selectedFiles,
      isDragging,
      fileInput,
      handleDragOver,
      handleDragLeave,
      handleDrop,
      triggerFileInput,
      handleFileSelect,
      removeFile,
      clearFiles,
      submitFiles,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.file-upload-container {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.upload-area {
  border: 3px dashed #cbd5e0;
  border-radius: 8px;
  padding: 60px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-area:hover,
.upload-area.dragging {
  border-color: #667eea;
  background-color: #f7fafc;
}

.upload-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.upload-area h3 {
  color: #2d3748;
  margin-bottom: 10px;
}

.upload-area p {
  color: #718096;
  font-size: 0.9rem;
}

.file-list {
  margin-top: 30px;
}

.file-list h4 {
  color: #2d3748;
  margin-bottom: 15px;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 15px;
  background: #f7fafc;
  border-radius: 6px;
  margin-bottom: 10px;
}

.file-name {
  flex: 1;
  color: #2d3748;
  font-weight: 500;
}

.file-size {
  color: #718096;
  font-size: 0.9rem;
  margin-right: 15px;
}

.remove-btn {
  background: #fc8181;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.remove-btn:hover {
  background: #f56565;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 20px;
}

.clear-btn,
.submit-btn {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn {
  background: #e2e8f0;
  color: #4a5568;
}

.clear-btn:hover {
  background: #cbd5e0;
}

.submit-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
