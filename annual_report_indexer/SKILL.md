# 年报结构定位器

## 描述
解析上市公司年度报告PDF文件，构建年报结构化章节索引。

本技能功能包括：
1. 解析目录页，识别一级章节及其起止页码
2. 精确定位“财务报告”章节
3. 在财务报告内部扫描识别：
   - 审计报告
   - 合并及母公司资产负债表
   - 合并及母公司利润表
   - 合并及母公司现金流量表
   - 合并及母公司所有者权益变动表
   - 财务报表附注
4. 输出结构化章节页码范围

本技能为后续：
- 财务报表抽取
- 三表勾稽校验
- 文本一致性核查
提供结构基础。

当用户要求：
- 定位年报章节
- 查找报表所在页
- 分析年报结构
- 构建审核结构索引
时调用此技能。

---

## 调用方式

- 脚本文件名：`skill.py`
- 函数名：`generate_audit_index_from_pdf`

---

## 调用代码示例

```python
import sys
sys.path.append(r'C:\Users\11975\AppData\Roaming\LobsterAI\SKILLs\annual_report_indexer')

from skill import generate_audit_index_from_pdf

result = generate_audit_index_from_pdf(r'PDF文件完整路径')
print(result)
