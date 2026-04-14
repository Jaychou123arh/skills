# 年报审核索引生成器

## 描述
解析上市公司年度报告PDF文件，生成模块化审核索引表。
优先解析目录页获取章节起止范围，支持跨页表格自动扩展。
当用户要求分析年报、生成索引、定位章节时调用此技能。

## 重要：调用方式
- 脚本文件名：skill.py
- 函数名：generate_audit_index_from_pdf
- 调用示例：
  ```python
  import sys
  sys.path.append(r'C:\Users\11975\AppData\Roaming\LobsterAI\SKILLs\annual_report_indexer')
  from skill import generate_audit_index_from_pdf
  result = generate_audit_index_from_pdf(pdf_path)
  print(result)
