# 文件名: skill.py

import pdfplumber
import re
import json
from collections import defaultdict

MODULE_TEMPLATES = {
    "模块1：报告结构与披露完整性": { "信息类型": "审计/治理意见型信息、文本叙述型信息", "审核对象": "审计意见类型、关键审计事项、关联交易披露、公司治理结构、内部控制评价", "审核动作": "提取、核对、对照、一致性审查", "预期输出": "披露项目清单、披露完整性评估", "调用说明": "后续应优先读取核心页段，逐项提取披露对象，并核对是否明确披露及是否存在披露不充分情形。" },
    "模块2：报表数字与基础勾稽关系": { "信息类型": "表格型信息", "审核对象": "资产负债表平衡关系、利润表勾稽、现金流量表分类、三表间勾稽关系", "审核动作": "提取、计算、勾稽检查、核对", "预期输出": "勾稽异常项列表、报表平衡性验证结果", "调用说明": "后续应提取四大报表核心数据，执行资产=负债+权益等基础勾稽检查。" },
    "模块3：盈利质量与现金流真实性": { "信息类型": "表格型信息、文本叙述型信息", "审核对象": "净利润、经营现金流、应收账款、存货、毛利率", "审核动作": "提取、计算、对照、分析", "预期输出": "现金流真实性判断、盈利质量评估", "调用说明": "后续将对比净利润与经营活动现金流，分析盈利的现金保障程度。" },
    "模块4：债务、流动性与持续经营风险": { "信息类型": "表格型信息、附注条目型信息", "审核对象": "资产负债率、流动比率、速动比率、有息负债、担保情况", "审核动作": "提取、计算、核对、红旗识别", "预期输出": "债务风险清单、流动性风险评估", "调用说明": "后续应计算关键债务和流动性指标，识别持续经营风险信号。" },
    "模块5：经营逻辑与业务合理性": { "信息类型": "文本叙述型信息", "审核对象": "业务模式描述、市场环境分析、竞争优势、发展战略", "审核动作": "提取、对照、一致性审查", "预期输出": "业务逻辑合理性评估、战略一致性检查", "调用说明": "后续应提取管理层讨论中的业务描述，验证其与财务数据的逻辑一致性。" },
    "模块6：文本表述与财务数据一致性": { "信息类型": "文本叙述型信息、表格型信息", "审核对象": "财务数据引用、业绩描述、趋势分析、预测性信息", "审核动作": "提取、核对、对照、一致性审查", "预期输出": "文本—数据偏差清单、表述准确性评估", "调用说明": "后续需对照管理层讨论中的文本描述与财务报表中的实际数据。" },
    "模块7：附注与重大事项深度审查": { "信息类型": "附注条目型信息、文本叙述型信息", "审核对象": "会计政策变更、关联交易、或有事项、承诺事项、重大诉讼", "审核动作": "提取、核对、深度分析、风险识别", "预期输出": "附注风险事项清单、重大事项影响评估", "调用说明": "后续需逐项审查财务报表附注，深度分析重大事项的财务影响。" },
    "模块8：治理、合规与审计信号": { "信息类型": "审计/治理意见型信息、文本叙述型信息", "审核对象": "治理结构、内部控制评价、审计意见、关键审计事项、监管处罚", "审核动作": "提取、核对、红旗识别", "预期输出": "治理合规风险清单、内控缺陷识别", "调用说明": "后续需提取公司治理、内控和审计报告信息，识别治理合规风险。" },
    "模块9：风险红旗综合识别": { "信息类型": "文本叙述型信息、附注条目型信息", "审核对象": "经营风险、财务风险、合规风险、行业风险、特殊风险事项", "审核动作": "提取、识别、分类、评估", "预期输出": "风险红旗清单、风险等级评估", "调用说明": "后续应综合各章节风险信息，识别和分类各类风险红旗。" }
}
KEYWORD_MODULE_MAP = { "审计报告": ["模块1", "模块8"], "财务报表": ["模块2", "模块6"], "资产负债表": ["模块2", "模块4"], "利润表": ["模块2", "模块3"], "现金流量表": ["模块2", "模块3"], "财务报表附注": ["模块4", "模块7", "模块9"], "管理层讨论与分析": ["模块3", "模块5", "模块6"], "风险提示": ["模块4", "模块9"], "重要事项": ["模块1", "模块7", "模块9"], "公司治理": ["模块1", "模块8"], "内部控制": ["模块1", "模块8"], "经营情况讨论与分析": ["模块5"], "股份变动及股东情况": ["模块8"] }

def generate_audit_index_from_pdf(pdf_path: str) -> str:
    found_sections = defaultdict(list)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        for keyword in KEYWORD_MODULE_MAP.keys():
                            # 更宽松的匹配，处理多种可能的章节标题格式
                            if re.search(r'(第[一二三四五六七八九十百]+[章节节]|摘要|目录|正文|附注)?\s*' + re.escape(keyword), line.strip(), re.IGNORECASE):
                                if (i + 1) not in found_sections[keyword]: 
                                    found_sections[keyword].append(i + 1)
    except Exception as e:
        return json.dumps({"error": f"处理PDF时发生错误: {e}"}, ensure_ascii=False, indent=2)
    
    final_index = {}
    for i in range(1, 10):
        module_name_prefix = f"模块{i}："
        # 找到完整的模块名称
        module_name = next((name for name in MODULE_TEMPLATES.keys() if name.startswith(module_name_prefix)), None)
        if module_name:
            final_index[module_name] = MODULE_TEMPLATES[module_name].copy()
            final_index[module_name]['核心章节'] = []
            final_index[module_name]['核心页段'] = []

    for keyword, pages in found_sections.items():
        related_modules = KEYWORD_MODULE_MAP.get(keyword, [])
        for module_num_str in related_modules:
            # 找到完整的模块名称
            module_name = next((name for name in MODULE_TEMPLATES.keys() if name.startswith(module_num_str)), None)
            if module_name and keyword not in final_index[module_name]['核心章节']: 
                final_index[module_name]['核心章节'].append(keyword)
            if module_name:
                final_index[module_name]['核心页段'].extend(pages)
    
    for module_name, details in final_index.items():
        if details['核心页段']:
            unique_sorted_pages = sorted(list(set(details['核心页段'])))
            
            # 尝试合并连续页码为范围
            page_ranges = []
            if unique_sorted_pages:
                start = unique_sorted_pages[0]
                end = unique_sorted_pages[0]
                for i in range(1, len(unique_sorted_pages)):
                    if unique_sorted_pages[i] == end + 1:
                        end = unique_sorted_pages[i]
                    else:
                        if start == end:
                            page_ranges.append(str(start))
                        else:
                            page_ranges.append(f"{start}-{end}")
                        start = unique_sorted_pages[i]
                        end = unique_sorted_pages[i]
                if start == end:
                    page_ranges.append(str(start))
                else:
                    page_ranges.append(f"{start}-{end}")
            details['核心页段'] = ", ".join(page_ranges)
        else:
            details['核心页段'] = "未自动定位"
        details['核心章节'] = ", ".join(details['核心章节']) if details['核心章节'] else "未自动定位"
        details['补充页段'] = "无明显补充页段"

    return json.dumps(final_index, ensure_ascii=False, indent=4)
