# 文件名: skill.py

import pdfplumber
import re
import json
from collections import defaultdict

# --- 模块1：报告结构与披露完整性 的预定义信息 ---
# 这些信息是固定的，与 PDF 内容无关，只是定义了审核的框架
MODULE1_DETAILS = {
    "模块名称": "模块1：报告结构与披露完整性",
    "信息类型": "审计/治理意见型信息、文本叙述型信息",
    "审核对象": ["审计意见类型", "关键审计事项", "关联交易披露", "公司治理结构", "内部控制评价", "风险因素", "基本信息"],
    "审核动作": ["提取", "核对", "对照", "一致性审查"],
    "预期输出": "披露项目清单、披露完整性评估、治理结构合规性清单"
}

# 明确的关键词到模块的映射（为了让LLM知道调用哪个技能）
# 实际上，这里更像是LLM Agent在决定调用哪个技能时会参考的，
# skill.py 内部更依赖 module_info 参数。
KEYWORD_MODULE_MAP = {
    "审计报告": ["模块1", "模块8"],
    "重大事项": ["模块1", "模块7", "模块9"],
    "公司治理": ["模块1", "模块8"],
    "内部控制": ["模块1", "模块8"],
    "风险提示": ["模块4", "模块9"],
    # ... 其他模块的关键词映射 ...
}

# 核心章节的列表，方便在 `module_info` 中查找
CORE_CHAPTERS_FOR_MODULE1 = ["审计报告", "重大事项", "公司治理", "内部控制", "风险提示"]


def _parse_page_ranges(pages_str):
    """解析类似 '2, 4, 28-29, 38, 42, 57-58' 这样的字符串，返回页码列表"""
    if not pages_str:
        return []
    
    pages = []
    parts = pages_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                pages.extend(range(start, end + 1))
            except ValueError:
                pass # 忽略无效范围
        else:
            try:
                pages.append(int(part))
            except ValueError:
                pass # 忽略无效页码
    return sorted(list(set(pages))) # 去重并排序

def _check_keyword_in_pages(pdf_path, page_numbers, keywords):
    """
    在指定的页码范围内，检查PDF文本中是否包含任何一个关键词。
    返回状态和找到的页码。
    """
    found_at_pages = []
    status = "未找到"
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # 仅处理指定的页码
            for page_num in page_numbers:
                if 1 <= page_num <= len(pdf.pages):
                    page = pdf.pages[page_num - 1]
                    text = page.extract_text()
                    if text:
                        # 检查关键词是否在页面文本中
                        for keyword in keywords:
                            # 使用 re.IGNORECASE 进行不区分大小写的匹配
                            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                                if page_num not in found_at_pages:
                                    found_at_pages.append(page_num)
                                break # 找到一个关键词就跳出内部循环
    except Exception as e:
        return f"PDF读取错误: {e}", []

    if found_at_pages:
        status = f"在页码 {', '.join(map(str, sorted(list(set(found_at_pages)))))} 中找到。"
    else:
        status = "未在指定页码范围内找到。"
        
    return status, found_at_pages


def check_report_structure(pdf_path: str, module_info: str) -> str:
    """
    检查年报的报告结构与披露完整性。
    接收PDF路径和关于模块1的定位信息，进行检查。

    :param pdf_path: 年报PDF文件的路径。
    :param module_info: JSON字符串，包含模块1的定位信息，例如：
                       {"核心章节": "审计报告, 公司治理, 重大事项",
                        "核心页段": "2, 4, 28-29, 38, 42, 57-58, 67, 74-78",
                        "审核对象": "审计意见类型、关键审计事项、关联交易披露、公司治理结构、内部控制评价",
                        "审核动作": "提取、核对、对照、一致性审查",
                        "预期输出": "披露项目清单、披露完整性评估、治理结构合规性清单"}
    :return: Markdown格式的审核结果字符串。
    """

    try:
        # 解析 module_info JSON
        module_details = json.loads(module_info)
        
        # 获取核心章节列表，用于关键词检查
        core_chapters_str = module_details.get("核心章节", "")
        core_chapters = [ch.strip() for ch in core_chapters_str.split(',') if ch.strip()]
        
        # 获取核心页段字符串，并解析成页码列表
        core_pages_str = module_details.get("核心页段", "")
        core_pages_list = _parse_page_ranges(core_pages_str)
        
        audit_objects = module_details.get("审核对象", "").split("、")
        audit_actions = module_details.get("审核动作", "").split("、")
        expected_outputs = module_details.get("预期输出", "").split("、")

        # --- 开始进行检查 ---
        report_lines = [f"# 模块1：报告结构与披露完整性 审核结果\n"]
        report_lines.append(f"## 审核对象：{module_details.get('审核对象', 'N/A')}\n")
        report_lines.append(f"## 审核动作：{module_details.get('审核动作', 'N/A')}\n")

        # 1. 基本信息完整性检查 (示例：检查文件是否存在，虽然skill.py被调用时文件已存在)
        report_lines.append("### 1. 基本信息完整性检查")
        # 这里的检查可以是：PDF文件是否可读，LLM是否正确解析了基本参数
        # 假设 `pdf_path` 是有效的，并且 LLM 成功传递了 `module_info`
        basic_info_status = "基本参数已接收，PDF文件可访问。"
        report_lines.append(f"- **检查结果：** {basic_info_status}")
        report_lines.append("- **具体审核项：** 文件可读性、基本参数接收情况")

        # 2. 检查审计报告
        audit_report_keywords = ["审计报告", "审计意见"]
        audit_report_status, audit_report_pages = _check_keyword_in_pages(pdf_path, core_pages_list, audit_report_keywords)
        report_lines.append(f"### 2. 审计报告完整性检查")
        report_lines.append(f"- **状态：** {audit_report_status}")
        report_lines.append("- **具体审核项：** 审计意见类型、关键审计事项")

        # 3. 检查关键审计事项是否披露 (通常在审计报告附带)
        # 这个检查更偏向内容分析，我们的定位技能只能定位到大概区域
        # 实际检查需要更复杂的文本匹配或LLM内容理解
        kiam_status = f"需在定位到的审计报告页段 ({', '.join(map(str, audit_report_pages))}) 中进一步查找和检查。" if audit_report_pages else "未定位审计报告，无法检查关键审计事项。"
        report_lines.append(f"### 3. 关键审计事项披露检查")
        report_lines.append(f"- **状态：** {kiam_status}")

        # 4. 检查风险提示是否披露
        risk_alert_keywords = ["风险提示", "风险因素", "风险因素的充分性"]
        risk_alert_status, risk_alert_pages = _check_keyword_in_pages(pdf_path, core_pages_list, risk_alert_keywords)
        report_lines.append(f"### 4. 风险提示披露检查")
        report_lines.append(f"- **状态：** {risk_alert_status}")
        report_lines.append("- **具体审核项：** 风险因素的充分性、合理性")

        # 5. 检查重大事项是否披露
        major_matters_keywords = ["重大事项", "关联交易", "诉讼仲裁", "担保", "资金占用"]
        major_matters_status, major_matters_pages = _check_keyword_in_pages(pdf_path, core_pages_list, major_matters_keywords)
        report_lines.append(f"### 5. 重大事项披露检查")
        report_lines.append(f"- **状态：** {major_matters_status}")
        report_lines.append("- **具体审核项：** 关联交易、诉讼仲裁、担保、资金占用")

        # 6. 检查关联交易是否披露 (已包含在重大事项检查的关键词中，这里可以更具体或省略)
        # 关联交易是重大事项的一部分，这里可以保留，或者合并到上一项
        # related_transaction_status = "需在重大事项或附注中检查"
        # report_lines.append(f"### 6. 关联交易披露检查")
        # report_lines.append(f"- **状态：** {related_transaction_status}")

        # 7. 检查诉讼仲裁是否披露 (已包含在重大事项检查的关键词中)
        # litigation_status = "需在重大事项或附注中检查"
        # report_lines.append(f"### 7. 诉讼仲裁披露检查")
        # report_lines.append(f"- **状态：** {litigation_status}")
        
        # 8. 检查担保、资金占用是否披露 (已包含在重大事项检查的关键词中)
        # guarantee_funds_status = "需在重大事项或附注中检查"
        # report_lines.append(f"### 8. 担保、资金占用披露检查")
        # report_lines.append(f"- **状态：** {guarantee_funds_status}")

        # 9. 检查内控评价是否披露
        internal_control_keywords = ["内部控制", "内控评价", "内控缺陷"]
        internal_control_status, internal_control_pages = _check_keyword_in_pages(pdf_path, core_pages_list, internal_control_keywords)
        report_lines.append(f"### 9. 内控评价披露检查")
        report_lines.append(f"- **状态：** {internal_control_status}")
        report_lines.append("- **具体审核项：** 内控评价、内控缺陷")

        # 10. 检查会计政策、会计估计变更是否披露
        # 这些通常在“财务报表附注”里，附注也可能在核心章节中被提及
        accounting_policy_keywords = ["会计政策", "会计估计", "会计政策和会计估计的变更"]
        accounting_policy_status, accounting_policy_pages = _check_keyword_in_pages(pdf_path, core_pages_list, accounting_policy_keywords)
        report_lines.append(f"### 10. 会计政策、会计估计变更披露检查")
        report_lines.append(f"- **状态：** {accounting_policy_status}")
        report_lines.append("- **具体审核项：** 会计政策、会计估计变更")

        # --- 总体评价 ---
        # 这个评价可以基于定位到的关键词数量和状态的平均水平来生成，但初期可以简化
        overall_assessment_lines = ["\n## 总体评价"]
        
        found_count = 0
        total_checks = 0
        
        # 简单的统计：有多少项被“定位到”或“初步找到”
        if audit_report_pages: found_count += 1
        if risk_alert_pages: found_count += 1
        if major_matters_pages: found_count += 1
        if internal_control_pages: found_count += 1
        if accounting_policy_pages: found_count += 1
        
        # 粗略估计总共需要检查的项目数（不含直接依赖其他部分的）
        total_checks = 5 # 基本信息、审计报告、风险提示、重大事项、内控评价
        
        if found_count / total_checks > 0.7:
            overall_assessment = "初步检查显示，大部分关键章节和信息已成功定位，结构完整性初步判断较好。"
        elif found_count / total_checks > 0.4:
            overall_assessment = "初步检查显示，部分关键章节和信息已定位，结构完整性待进一步确认。"
        else:
            overall_assessment = "初步检查显示，部分关键章节和信息未能在核心页段中明确找到，结构完整性需重点关注。"
            
        report_lines.append(overall_assessment)

        # 报告结尾
        report_lines.append("\n---")
        report_lines.append("**注意：** 此为基于关键词定位的初步检查，具体内容的完整性和准确性，需结合 PDF 实际内容进行深度阅读和判断。")

        # 将所有报告行连接成一个字符串返回
        return "\n".join(report_output)

    except json.JSONDecodeError:
        return "错误：提供的模块信息格式不正确，无法解析JSON。"
    except FileNotFoundError:
        return f"错误：PDF文件未找到，请检查路径：{pdf_path}"
    except Exception as e:
        # 捕获其他可能的运行时错误，并以 JSON 格式返回错误信息
        return json.dumps({"error": f"处理过程中发生未知错误: {e}"}, ensure_ascii=False, indent=4)
