const API_BASE_URL = 'http://localhost:8000/api'

export async function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData
  })
  
  if (!response.ok) {
    throw new Error('文件上传失败')
  }
  
  return await response.json()
}

export async function createSubmission(fileIds) {
  const response = await fetch(`${API_BASE_URL}/submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(fileIds)
  })
  
  if (!response.ok) {
    throw new Error('创建提交失败')
  }
  
  return await response.json()
}

export async function verifySubmission(submissionId) {
  const response = await fetch(`${API_BASE_URL}/verify/${submissionId}`, {
    method: 'POST'
  })
  
  if (!response.ok) {
    throw new Error('开始验证失败')
  }
  
  return await response.json()
}

export async function verifySubmissionFile(submissionId, fileId) {
  const response = await fetch(`${API_BASE_URL}/verify/${submissionId}/file/${fileId}`, {
    method: 'POST'
  })

  if (!response.ok) {
    throw new Error('开始单文件验证失败')
  }

  return await response.json()
}

export async function getSubmissionStatus(submissionId) {
  const response = await fetch(`${API_BASE_URL}/status/${submissionId}`)
  
  if (!response.ok) {
    throw new Error('获取状态失败')
  }
  
  return await response.json()
}

export async function getSubmissionResults(submissionId) {
  const response = await fetch(`${API_BASE_URL}/results/${submissionId}`)
  
  if (!response.ok) {
    throw new Error('获取结果失败')
  }
  
  return await response.json()
}

export async function getAllSubmissions(limit = 50) {
  const response = await fetch(`${API_BASE_URL}/submissions?limit=${limit}`)
  
  if (!response.ok) {
    throw new Error('获取历史记录失败')
  }
  
  return await response.json()
}

export async function replaceSubmissionFile(submissionId, oldFileId, newFileId, filename) {
  const response = await fetch(`${API_BASE_URL}/submissions/${submissionId}/replace-file`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      old_file_id: oldFileId,
      new_file_id: newFileId,
      filename
    })
  })

  if (!response.ok) {
    throw new Error('替换文件失败')
  }

  return await response.json()
}
