// API基础URL
const API_BASE = 'http://localhost:5000';

// 生成唯一会话ID
const SESSION_ID = 'session_' + Date.now();

// DOM元素
const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const resetBtn = document.getElementById('resetBtn');

// 添加消息到对话框
function addMessage(content, type = 'bot') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (typeof content === 'string') {
        // 处理换行符
        const paragraphs = content.split('\n').filter(p => p.trim());
        paragraphs.forEach(p => {
            const pEl = document.createElement('p');
            pEl.textContent = p;
            contentDiv.appendChild(pEl);
        });
    } else {
        contentDiv.appendChild(content);
    }
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // 滚动到底部
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 添加系统消息
function addSystemMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 添加加载消息
function addLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.id = 'loading-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<p class="loading">处理中</p>';
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageDiv;
}

// 移除加载消息
function removeLoadingMessage() {
    const loadingMsg = document.getElementById('loading-message');
    if (loadingMsg) {
        loadingMsg.remove();
    }
}

// 上传PDF文件
async function uploadPDF(file) {
    const loadingMsg = addLoadingMessage();
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', SESSION_ID);
        
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        removeLoadingMessage();
        
        if (data.error) {
            addMessage(`❌ 错误：${data.error}`, 'bot');
            return;
        }
        
        // 显示上传成功
        addSystemMessage(`✅ 已上传：${data.filename}`);
        
        // 显示验证结果
        if (data.answer) {
            addMessage(data.answer, 'bot');
        }
        
        // 显示详细工具结果（可选）
        if (data.tool_results && data.tool_results.length > 0) {
            data.tool_results.forEach(result => {
                if (result.detail) {
                    let detailText = '\n📊 详细信息：';
                    if (result.detail.title) detailText += `\n标题：${result.detail.title}`;
                    if (result.detail.doi) detailText += `\nDOI：${result.detail.doi}`;
                    if (result.detail.publisher) detailText += `\n出版商：${result.detail.publisher}`;
                    if (result.detail.matched_authors) {
                        detailText += `\n匹配作者：${result.detail.matched_authors.join(', ')}`;
                    }
                    addSystemMessage(detailText);
                }
            });
        }
        
    } catch (error) {
        removeLoadingMessage();
        addMessage(`❌ 上传失败：${error.message}`, 'bot');
    }
}

// 发送消息
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // 显示用户消息
    addMessage(message, 'user');
    messageInput.value = '';
    
    // 禁用输入
    sendBtn.disabled = true;
    messageInput.disabled = true;
    
    const loadingMsg = addLoadingMessage();
    
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: SESSION_ID
            })
        });
        
        const data = await response.json();
        
        removeLoadingMessage();
        
        if (data.error) {
            addMessage(`❌ 错误：${data.error}`, 'bot');
        } else if (data.reply) {
            addMessage(data.reply, 'bot');
        }
        
    } catch (error) {
        removeLoadingMessage();
        addMessage(`❌ 发送失败：${error.message}`, 'bot');
    } finally {
        sendBtn.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// 重置会话
async function resetSession() {
    if (!confirm('确定要重置会话吗？所有对话历史将被清除。')) {
        return;
    }
    
    try {
        await fetch(`${API_BASE}/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: SESSION_ID
            })
        });
        
        // 清空消息区域
        messagesContainer.innerHTML = '';
        
        // 添加欢迎消息
        addMessage('👋 您好！我是论文验证助手。\n请上传您的论文PDF，我将帮您验证论文的真实性及作者归属。', 'bot');
        
    } catch (error) {
        addMessage(`❌ 重置失败：${error.message}`, 'bot');
    }
}

// 事件监听
uploadBtn.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            addMessage('❌ 请选择PDF格式的文件', 'bot');
            return;
        }
        uploadPDF(file);
    }
    // 清空input，允许重复上传同一文件
    fileInput.value = '';
});

sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

resetBtn.addEventListener('click', resetSession);

// 页面加载时聚焦输入框
messageInput.focus();
