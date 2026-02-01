<!-- filepath: e:\scholarship\frontend\src\components\ResultCard.vue -->
<template>
  <div class="result-card">
    <div class="result-header">
      <div class="file-info">
        <span class="file-icon">📄</span>
        <h3 class="file-name">{{ result.filename }}</h3>
        <span class="status-badge" :class="statusClass">{{ statusText }}</span>
      </div>
    </div>

    <div class="result-content">
      <!-- AI 结论 -->
      <div v-if="aiConclusion" class="conclusion-section">
        <h4>🤖 AI 分析结论</h4>
        <div class="conclusion-text">{{ aiConclusion }}</div>
      </div>

      <!-- 工具验证结果 -->
      <div v-if="toolResults && toolResults.length > 0" class="tools-section">
        <h4>🔍 验证工具结果</h4>
        <div class="tool-results">
          <div 
            v-for="(tool, index) in toolResults" 
            :key="index"
            class="tool-result-item"
            :class="getToolStatusClass(tool)"
          >
            <!-- 头部概览 -->
            <div class="tool-header-row">
              <span class="tool-icon">🔧</span>
              <span class="tool-name">{{ getToolName(tool) }}</span>
              <span class="tool-status-tag">
                {{ getToolStatus(tool) }}
              </span>
            </div>

            <!-- 结果消息 (直接显示) -->
            <div v-if="getToolMessage(tool)" class="tool-message-row">
               {{ getToolMessage(tool) }}
            </div>

            <details class="tool-details">
              <summary class="tool-summary-text">查看原始数据</summary>
              <div class="tool-content">
                <pre>{{ JSON.stringify(tool, null, 2) }}</pre>
              </div>
            </details>
          </div>
        </div>
      </div>

      <!-- 如果没有工具结果 -->
      <div v-if="!toolResults || toolResults.length === 0" class="no-tools">
        <p>⚠️ 未调用验证工具</p>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'ResultCard',
  props: {
    result: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    // 智能获取 AI 结论
    const aiConclusion = computed(() => {
      return props.result.result?.ai_conclusion || 
             props.result.conclusion || 
             props.result.ai_conclusion || 
             null;
    });
    
    // 智能获取工具结果
    const toolResults = computed(() => {
      const tools = props.result.result?.tool_results || 
             props.result.tool_results || 
             [];
      return Array.isArray(tools) ? tools : [];
    });

    // 计算真实的验证状态（综合后端状态和工具结果）
    const actualStatus = computed(() => {
      let status = props.result.status || props.result.result?.verification_status || 'unknown';
      
      // 如果后端说是成功，我们再仔细检查一下工具结果
      if (status === 'success' || status === 'completed') {
        const tools = toolResults.value;
        if (tools && tools.length > 0) {
          // 检查是否有任何工具失败
          const hasFailure = tools.some(t => {
            if (!t) return true; // null 结果视为失败
            // 检查 verified 字段
            if (t.verified === false) return true;
            // 检查 status 字段
            const s = (t.status || t.result || '').toLowerCase();
            return s === 'error' || s === 'failed' || s.includes('失败') || s.includes('错误');
          });
          
          if (hasFailure) {
            return 'failed';
          }
        }
      }
      return status;
    });
    
    const statusClass = computed(() => {
      const status = actualStatus.value;
      const classMap = {
        success: 'status-success',
        completed: 'status-success',
        warning: 'status-warning',
        error: 'status-error',
        failed: 'status-error'
      };
      return classMap[status] || 'status-unknown';
    });

    const statusText = computed(() => {
      const status = actualStatus.value;
      const textMap = {
        success: '✅ 验证通过',
        completed: '✅ 验证通过',
        warning: '⚠️ 需要注意',
        error: '❌ 验证失败',
        failed: '❌ 验证失败'
      };
      return textMap[status] || '❓ 未知状态';
    });

    const getToolName = (tool) => {
      if (!tool) return '未知工具';
      if (typeof tool === 'string') return '验证工具';
      return tool.tool_name || tool.name || '验证工具';
    };

    const getToolStatus = (tool) => {
      if (!tool) return '失败';
      if (typeof tool === 'string') return tool;
      return tool.status || tool.result || '未知';
    };

    const getToolMessage = (tool) => {
      if (!tool) return '';
      if (typeof tool === 'string') return '';
      const msg = tool.message || tool.msg || tool.error;
      if (typeof msg === 'object') return JSON.stringify(msg);
      return msg || '';
    };

    const getToolStatusClass = (tool) => {
      if (!tool) return 'tool-error';
      const status = typeof tool === 'string' ? tool : (tool.status || tool.result || '');
      const statusLower = typeof status === 'string' ? status.toLowerCase() : '';
      const verified = tool.verified;
      
      // 优先检查 verified 字段
      if (verified === false) {
        return 'tool-error';
      }
      if (verified === true) {
        return 'tool-success';
      }
      
      // 检查 status 字段
      if (statusLower === 'success' || statusLower.includes('成功') || statusLower.includes('通过')) {
        return 'tool-success';
      }
      if (statusLower === 'error' || statusLower === 'failed' || statusLower.includes('失败') || statusLower.includes('错误')) {
        return 'tool-error';
      }
      if (statusLower === 'warning' || statusLower.includes('警告') || statusLower.includes('注意')) {
        return 'tool-warning';
      }
      
      return 'tool-warning';
    };

    return {
      statusClass,
      statusText,
      getToolName,
      getToolStatus,
      getToolStatusClass,
      getToolMessage,
      aiConclusion,
      toolResults
    };
  }
};
</script>

<style scoped>
.result-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.result-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.result-header {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.file-info {
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
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}

.status-success {
  background: #d1fae5;
  color: #065f46;
}

.status-warning {
  background: #fef3c7;
  color: #92400e;
}

.status-error {
  background: #fee2e2;
  color: #991b1b;
}

.status-unknown {
  background: #f3f4f6;
  color: #6b7280;
}

.result-content {
  padding: 16px;
}

.conclusion-section {
  margin-bottom: 20px;
}

.conclusion-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.conclusion-text {
  padding: 12px;
  background: #f9fafb;
  border-left: 3px solid #667eea;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2937;
  white-space: pre-wrap;
}

.tools-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.tool-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-result-item {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.tool-result-item.tool-success {
  border-left: 4px solid #10b981;
}

.tool-result-item.tool-warning {
  border-left: 4px solid #f59e0b;
}

.tool-result-item.tool-error {
  border-left: 4px solid #ef4444;
}

.tool-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #f3f4f6;
  background: #f9fafb;
}

.tool-icon {
  font-size: 16px;
}

.tool-name {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  flex: 1;
}

.tool-status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(0,0,0,0.05);
  font-weight: 500;
}

/* 状态标签样式复用 */
.tool-success .tool-status-tag {
  color: #059669;
  background: #ecfdf5;
}
.tool-warning .tool-status-tag {
  color: #d97706;
  background: #fffbeb;
}
.tool-error .tool-status-tag {
  color: #dc2626;
  background: #fef2f2;
}

.tool-message-row {
  padding: 12px;
  font-size: 14px;
  color: #1f2937;
  line-height: 1.5;
  background: white;
  border-bottom: 1px solid #f3f4f6;
  white-space: pre-wrap;
}

/* 根据状态改变消息文字颜色 */
.tool-error .tool-message-row {
  color: #b91c1c;
  background: #fff5f5;
}

.tool-success .tool-message-row {
  color: #047857;
  background: #f0fdf4;
}

.tool-details {
  background: #fcfcfc;
}

.tool-summary-text {
  padding: 8px 12px;
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
  list-style: none; /* 某些浏览器 */
}

.tool-summary-text:hover {
  color: #374151;
  background: #f3f4f6;
}

.tool-content {
  padding: 12px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.tool-content pre {
  margin: 0;
  padding: 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  font-size: 12px;
  color: #374151;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.no-tools {
  padding: 20px;
  text-align: center;
  color: #6b7280;
  background: #f9fafb;
  border-radius: 6px;
}

.no-tools p {
  margin: 0;
  font-size: 14px;
}
</style>