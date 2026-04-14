import pdfplumber
import re
import json
from collections import defaultdict
import os

MODULE_TEMPLATES = {
    "模块1：报告结构与披露完整性": {
        "信息类型": "审计/治理意见型信息、文本叙述型信息",
        "审核对象": "审计意见类型、关键审计事项、关联交易披露、公司治理结构、内部控制评价",
        "审核动作": "提取、核对、对照、一致性审查",
        "预期输出": "披露项目清单、披露完整性评估、治理结构合规性清单",
        "调用说明": "优先读取审计报告和重大事项部分，逐项提取披露对象，核对是否完整披露。"
    },
    "模块2：报表数字与基础勾稽关系": {
        "信息类型": "表格型信息",
        "审核对象": "资产负债表平衡关系、利润表勾稽、现金流量表、三表间勾稽关系",
        "审核动作": "提取、计算、勾稽检查、核对",
        "预期输出": "勾稽异常项列表、报表平衡性验证结果、三表一致性检查清单",
        "调用说明": "提取四大报表核心数据，执行资产=负债+权益等基础勾稽检查。"
    },
    "模块3：盈利质量与现金流真实性": {
        "信息类型": "表格型信息、文本叙述型信息",
        "审核对象": "净利润、经营现金流、投资现金流、筹资现金流、盈利质量指标",
        "审核动作": "提取、计算、对照、分析",
        "预期输出": "现金流真实性判断、盈利质量评估、现金流与利润匹配度分析",
        "调用说明": "对比净利润与经营活动现金流，分析盈利的现金保障程度。"
    },
    "模块4：债务、流动性与持续经营风险": {
        "信息类型": "表格型信息、附注条目型信息",
        "审核对象": "资产负债率、流动比率、速动比率、有息负债、担保情况",
        "审核动作": "提取、计算、核对、红旗识别",
        "预期输出": "债务风险清单、流动性风险评估、持续经营风险判断",
        "调用说明": "计算关键债务和流动性指标，识别持续经营风险信号。"
    },
    "模块5：经营逻辑与业务合理性": {
        "信息类型": "文本叙述型信息",
        "审核对象": "业务模式描述、市场环境分析、竞争优势、发展战略",
        "审核动作": "提取、对照、一致性审查、逻辑验证",
        "预期输出": "业务逻辑合理性评估、战略一致性检查",
        "调用说明": "提取管理层讨论中的业务描述，验证与财务数据的逻辑一致性。"
    },
    "模块6：文本表述与财务数据一致性": {
        "信息类型": "文本叙述型信息、表格型信息",
        "审核对象": "财务数据引用、业绩描述、趋势分析、预测性信息",
        "审核动作": "提取、核对、对照、一致性审查",
        "预期输出": "文本—数据偏差清单、表述准确性评估",
        "调用说明": "对照管理层讨论中的文本描述与财务报表实际数据，检查一致性。"
    },
    "模块7：附注与重大事项深度审查": {
        "信息类型": "附注条目型信息、文本叙述型信息",
        "审核对象": "会计政策变更、估计变更、关联交易、或有事项、重大诉讼",
        "审核动作": "提取、核对、深度分析、风险识别",
        "预期输出": "附注风险事项清单、重大事项影响评估",
        "调用说明": "逐项审查财务报表附注，深度分析重大事项的财务影响。"
    },
    "模块8：治理、合规与审计信号": {
        "信息类型": "审计/治理意见型信息、文本叙述型信息",
        "审核对象": "治理结构、内部控制评价、审计意见、关键审计事项、监管处罚",
        "审核动作": "提取、核对、红旗识别、合规检查",
        "预期输出": "治理合规风险清单、内控缺陷识别、审计信号分析",
        "调用说明": "提取公司治理和内控信息，识别治理合规风险。"
    },
    "模块9：风险红旗综合识别": {
        "信息类型": "文本叙述型信息、附注条目型信息",
        "审核对象": "经营风险、财务风险、合规风险、行业风险",
        "审核动作": "提取、识别、分类、评估",
        "预期输出": "风险红旗清单、风险等级评估、风险应对建议",
        "调用说明": "综合各章节风险信息，识别和分类各类风险红旗。"
    }
}

KEYWORD_MODULE_MAP = {
    "审计报告": ["模块1", "模块8"],
    "财务报表": ["模块2", "模块6"],
    "资产负债表": ["模块2", "模块4"],
    "利润表": ["模块2", "模块3"],
    "现金流量表": ["模块2", "模块3"],
    "所有者权益变动表": ["模块2"],
    "财务报表附注": ["模块4", "模块7", "模块9"],
    "管理层讨论与分析": ["模块3", "模块5", "模块6"],
    "风险提示": ["模块4", "模块9"],
    "重大事项": ["模块1", "模块7", "模块9"],
    "公司治理": ["模块1", "模块8"],
    "内部控制": ["模块1", "模块8"],
    "主营业务": ["模块5"],
    "经营情况": ["模块5"],
    "股份变动": ["模块8"],
    "股东情况": ["模块8"]
}

KEY_CHAPTERS_TO_LOCATE = [
    "审计报告", "财务报表", "财务报表附注",
    "管理层讨论与分析", "风险提示", "重大事项",
    "公司治理", "内部控制", "主营业务", "股份变动"
]


def _format_page_ranges(pages_list):
    """将页码列表格式化为 '1, 2-3, 5' 这样的字符串"""
    if not pages_list:
        return "未定位"
    
    unique_sorted = sorted(list(set(pages_list)))
    ranges = []
    start = end = unique_sorted[0]
    
    for p in unique_sorted[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
            start = end = p
    
    ranges.append(str(start) if start == end else f"{start}-{end}")
    return ", ".join(ranges)


def generate_audit_index_from_pdf(pdf_path: str) -> str:
    """
    读取PDF，解析章节和页码，生成JSON格式的审核索引。
    """
    if not os.path.exists(pdf_path):
        return json.dumps(
            {"error": f"PDF文件未找到：{pdf_path}"},
            ensure_ascii=False, indent=4
        )

    found_sections = defaultdict(list)
    key_chapter_locations = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                text = page.extract_text()
                if not text:
                    continue
                    
                for line in text.split('\n'):
                    line = line.strip()
                    if len(line) > 100:
                        continue
                        
                    # 匹配关键词到模块
                    for keyword in KEYWORD_MODULE_MAP.keys():
                        if keyword in line:
                            if page_num not in found_sections[keyword]:
                                found_sections[keyword].append(page_num)
                    
                    # 记录关键章节首次出现位置
                    for chapter in KEY_CHAPTERS_TO_LOCATE:
                        if chapter in line and chapter not in key_chapter_locations:
                            key_chapter_locations[chapter] = page_num

    except Exception as e:
        return json.dumps(
            {"error": f"处理PDF时发生错误: {str(e)}"},
            ensure_ascii=False, indent=4
        )

    # 构建模块索引
    final_index = {}
    for module_name, template in MODULE_TEMPLATES.items():
        module_num = module_name[:3]  # "模块1"
        
        core_chapters = []
        core_pages = []
        
        for keyword, modules in KEYWORD_MODULE_MAP.items():
            if module_num in modules and keyword in found_sections:
                if keyword not in core_chapters:
                    core_chapters.append(keyword)
                core_pages.extend(found_sections[keyword])
        
        final_index[module_name] = {
            **template,
            "核心章节": ", ".join(core_chapters) if core_chapters else "未自动定位",
            "核心页段": _format_page_ranges(core_pages),
            "补充页段": "无明显补充页段"
        }

    # 关键章节定位
    key_chapters_output = {}
    for chapter in KEY_CHAPTERS_TO_LOCATE:
        page = key_chapter_locations.get(chapter, "未定位")
        all_pages = found_sections.get(chapter, [])
        
        if page != "未定位":
            formatted = _format_page_ranges(all_pages)
            key_chapters_output[chapter] = (
                f"第{page}页（另见{formatted}页）"
                if formatted and str(page) != formatted
                else f"第{page}页"
            )
        else:
            key_chapters_output[chapter] = "未定位"

    result = {
        "审核索引表": {
            "模块化可执行审核索引": final_index,
            "关键章节定位": key_chapters_output,
            "质量说明": {
                "可直接审核模块": ["模块1", "模块2", "模块8"],
                "需精细校准模块": ["模块5", "模块6", "模块9"],
                "建议优先审核": ["模块1", "模块2", "模块8"]
            }
        }
    }

    return json.dumps(result, ensure_ascii=False, indent=4)
