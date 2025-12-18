# 学籍验证工具 (Certificate Verify)

## 功能说明

通过学信网在线验证码验证学籍证明的真实性。

## 使用方法

```python
from services.certificate_verify import certificate_verify

# 验证学籍证明
vcode = "ACY3RBVSBQQDN6Z1"
result = certificate_verify(vcode)

if result:
    print("验证通过！")
    print(result)  # Markdown 格式的学籍信息
else:
    print("验证码无效")
```

## 参数说明

- **vcode** (str): 学信网在线验证码，格式如 `ACY3RBVSBQQDN6Z1`

## 返回值

- **成功**: 返回学籍信息的 Markdown 格式字符串，包含：
  - 姓名、性别、出生日期
  - 学校名称、层次、专业
  - 学制、学历类别、学习形式
  - 入学日期、学籍状态、预计毕业日期
  - 等其他学籍信息

- **失败**: 返回 `None`（验证码无效或网络错误）

## 技术实现

使用 Playwright 模拟浏览器访问学信网，绕过反爬虫机制：

1. 使用无头浏览器（Chromium）
2. 设置真实的浏览器指纹（User-Agent、viewport等）
3. 等待反爬虫机制完成并重新加载页面（约10秒）
4. 提取 `#resultTable` 元素内容
5. 转换为 Markdown 格式返回

## 注意事项

1. **需要 Playwright 环境**：确保已安装 playwright 及浏览器驱动
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **执行时间**：由于需要等待反爬虫验证，单次查询约需 10-15 秒

3. **验证码有效期**：学信网验证码有效期为 1-6 个月，由报告权属人设置