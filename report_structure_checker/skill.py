# 文件名: skill.py (report_structure_checker 文件夹下)

import pdfplumber
import re
import json
from collections import defaultdict

# ... (MODULE_TEMPLATES, KEYWORD_MODULE_MAP, CORE_CHAPTERS_FOR_MODULE1 等配置信息) ...

def _format_page_ranges(pages_str): # 假设你保留了页码格式化函数
    # ... (实现) ...
    pass # 简化

def check_report_structure(pdf_path: str, module_info: str) -> str:
    """
    检查年报的报告结构与披露完整性。
    接收PDF路径和关于模块1的定位信息（JSON字符串），进行检查。
    """
    try:
        # 1. 解析 module_info JSON (这一步是关键，它承接了上一步的结果)
        module_details = json.loads(module_info)
        
        core_chapters_str = module_details.get("核心章节", "")
        core_chapters = [ch.strip() for ch in core_chapters_str.split(',') if ch.strip()]
        
        core_pages_str = module_details.get("核心页段", "")
        core_pages_list = _parse_page_ranges(core_pages_str) # 解析上一步传来的页码
        
        audit_objects = module_details.get("审核对象", "").split("、")
        audit_actions = module_details.get("审核动作", "").split("、")
        expected_outputs = module_details.get("预期输出", "").split("、")

        # --- 开始进行检查 ---
        report_lines = [f"# 模块1：报告结构与披露完整性 审核结果\n"]
        report_lines.append(f"## 审核对象：{module_details.get('审核对象', 'N/A')}\n")
        report_lines.append(f"## 审核动作：{module_details.get('审核动作', 'N/A')}\n")

        # ... (下面是对 PDF 的实际检查逻辑，使用 core_pages_list 等信息) ...
        # 这里进行 PDF 扫描，查找关键词，并根据查找结果更新状态
        
        # 示例：检查审计报告
        audit_report_keywords = ["审计报告", "审计意见"]
        audit_report_status, audit_report_pages = _check_keyword_in_pages(pdf_path, core_pages_list, audit_report_keywords)
        report_lines.append(f"### 2. 审计报告完整性检查")
        report_lines.append(f"- **状态：** {audit_report_status}")
        report_lines.append("- **具体审核项：** 审计意见类型、关键审计事项")
        
        # ... (继续对其他审核对象进行检查) ...

        # 最终返回 Markdown 字符串
        return "\n".join(report_output)

    except json.JSONDecodeError:
        return "错误：提供的模块信息格式不正确，无法解析JSON。"
    except FileNotFoundError:
        return f"错误：PDF文件未找到，请检查路径：{pdf_path}"
    except Exception as e:
        return f"处理过程中发生错误: {e}"
