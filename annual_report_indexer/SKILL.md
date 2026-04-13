# Skill: 年报审核索引生成器 (generate_audit_index_from_pdf)

## 描述 (Description)
本技能用于解析上市公司年度报告PDF文件。当用户要求对年报进行初步分析、建立导航、生成审核索引或定位关键章节时，LLM应该调用此工具。它接收一个PDF文件路径作为输入，并返回一个JSON格式的《模块化可执行审核索引表》，该表详细列出了9个核心审核模块所需关注的章节名称和页码范围。

## 参数 (Parameters)
### `pdf_path` (字符串, 必需)
需要分析的本地PDF文件的完整路径。

## Python 入口 (Python Entry Point)
文件名: `skill.py`
函数名: `generate_audit_index_from_pdf`

## Python 依赖 (Python Dependencies)
请参考 `requirements.txt` 文件。
