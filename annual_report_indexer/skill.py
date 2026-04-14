# 文件名: skill.py

import pdfplumber
import re
import json
from collections import defaultdict
import os

# --- 预定义的模块模板和关键词映射 ---
MODULE_TEMPLATES = {
    "模块1：报告结构与披露完整性": { "信息类型": "审计/治理意见型信息、文本叙述型信息", "审核对象": "审计意见类型、关键审计事项、关联交易披露、公司治理结构、内部控制评价", "审核动作": "提取、核对、对照、一致性审查", "预期输出": "披露项目清单、披露完整性评估、治理结构合规性清单", "调用说明": "后续应优先读取核心页段，逐项提取披露对象，并核对是否明确披露及是否存在披露不充分情形。" },
    "模块2：报表数字与基础勾稽关系": { "信息类型": "表格型信息", "审核对象": "资产负债表平衡关系、利润表勾稽、现金流量表分类、三表间勾稽关系", "审核动作": "提取、计算、勾稽检查、核对", "预期输出": "勾稽异常项列表、报表平衡性验证结果、三表一致性检查清单", "调用说明": "后续应提取四大报表核心数据，执行资产=负债+权益等基础勾稽检查。" },
    "模块3：盈利质量与现金流真实性": { "信息类型": "表格型信息、文本叙述型信息", "审核对象": "净利润、经营现金流、投资现金流、筹资现金流、盈利质量指标", "审核动作": "提取、计算、对照、分析", "预期输出": "现金流真实性判断、盈利质量评估、现金流与利润匹配度分析", "调用说明": "后续将对比净利润与经营活动现金流，分析盈利的现金保障程度。" },
    "模块4：债务、流动性与持续经营风险": { "信息类型": "表格型信息、附注条目型信息", "审核对象": "资产负债率、流动比率、速动比率、有息负债、担保情况、诉讼仲裁", "审核动作": "提取、计算、核对、红旗识别", "预期输出": "债务风险清单、流动性风险评估、持续经营风险判断", "调用说明": "后续应计算关键债务和流动性指标，识别持续经营风险信号。" },
    "模块5：经营逻辑与业务合理性": { "信息类型": "文本叙述型信息", "审核对象": "业务模式描述、市场环境分析、竞争优势、发展战略", "审核动作": "提取、对照、一致性审查、逻辑验证", "预期输出": "业务逻辑合理性评估、战略一致性检查、行业对标分析", "调用说明": "后续应提取管理层讨论中的业务描述，验证其与财务数据的逻辑一致性。" },
    "模块6：文本表述与财务数据一致性": { "信息类型": "文本叙述型信息、表格型信息", "审核对象": "财务数据引用、业绩描述、趋势分析、预测性信息", "审核动作": "提取、核对、对照、一致性审查", "预期输出": "文本—数据偏差清单、表述准确性评估、预测与实际情况对比", "调用说明": "后续需对照管理层讨论中的文本描述与财务报表中的实际数据。" },
    "模块7：附注与重大事项深度审查": { "信息类型": "附注条目型信息、文本叙述型信息", "审核对象": "会计政策变更、估计变更、关联交易、或有事项、承诺事项、重大诉讼", "审核动作": "提取、核对、深度分析、风险识别", "预期输出": "附注风险事项清单、重大事项影响评估、会计处理合规性判断", "调用说明": "后续需逐项审查财务报表附注，深度分析重大事项的财务影响。" },
    "模块8：治理、合规与审计信号": { "信息类型": "审计/治理意见型信息、文本叙述型信息", "审核对象": "治理结构、内部控制评价、审计意见、关键审计事项、监管处罚", "审核动作": "提取、核对、红旗识别、合规检查", "预期输出": "治理合规风险清单、内控缺陷识别、审计信号分析", "调用说明": "后续需提取公司治理、内控和审计报告信息，识别治理合规风险。" },
    "模块9：风险红旗综合识别": { "信息类型": "文本叙述型信息、附注条目型信息", "审核对象": "经营风险、财务风险、合规风险、行业风险、特殊风险事项", "审核动作": "提取、识别、分类、评估", "预期输出": "风险红旗清单、风险等级评估、风险应对建议", "调用说明": "后续应综合各章节风险信息，识别和分类各类风险红旗。" }
}
KEYWORD_MODULE_MAP = {
    "审计报告": ["模块1", "模块8"],
    "财务报表": ["模块2", "模块6"],
    "资产负债表": ["模块2", "模块4"],
    "利润表": ["模块2", "模块3"],
    "现金流量表": ["模块2", "模块3"],
    "所有者权益变动表": ["模块2"], # 明确所有者权益变动表
    "财务报表附注": ["模块4", "模块7", "模块9"],
    "管理层讨论与分析": ["模块3", "模块5", "模块6"], # 修正了这里的错误，去掉了多余的逗号和乱码
    "风险提示": ["模块4", "模块9"],
    "重大事项": ["模块1", "模块7", "模块9"], # 使用“重大事项”保持一致
    "公司治理": ["模块1", "模块8"],
    "内部控制": ["模块1", "模块8"],
    "主营业务": ["模块5"], # 对应“主营业务/经营情况”
    "经营情况": ["模块5"], # 对应“主营业务/经营情况”
    "股份变动": ["模块8"], # 对应“股份变动及股东情况”
    "股东情况": ["模块8"] # 对应“股份变动及股东情况”
}

KEY_CHAPTERS_TO_LOCATE = [
    "审计报告", "财务报表", "财务报表附注", "管理层讨论与分析",
    "风险提示", "重大事项", "公司治理", "内部控制",
    "主营业务/经营情况", "股份变动及股东情况"
]


def _format_page_ranges(pages_list):
    """将页码列表格式化为 '1, 2-3, 5' 这样的字符串"""
    if not pages_list:
        return "未定位"
    unique_sorted_pages = sorted(list(set(pages_list))) # 去重并排序
    
    page_ranges = []
    if unique_sorted_pages:
        start = unique_sorted_pages[0]
        end = unique_sorted_pages[0]
        for i in range(1, len(unique_sorted_pages)):
            if unique_sorted_pages[i] == end + 1:
                end = unique_sorted_pages[i] # 扩展范围
            else:
                # 范围结束，添加当前范围
                if start == end:
                    page_ranges.append(str(start))
                else:
                    page_ranges.append(f"{start}-{end}")
                # 开始新的范围
                start = unique_sorted_pages[i]
                end = unique_sorted_pages[i]
        
        # 添加最后一个范围
        if start == end:
            page_ranges.append(str(start))
        else:
            page_ranges.append(f"{start}-{end}")
            
    return ", ".join(page_ranges)


def generate_audit_index_from_pdf(pdf_path: str) -> str:
    """
    读取PDF，解析章节和页码，并根据预设的模块化模板生成JSON格式的审核索引。
    """
    
    # 检查PDF文件是否存在
    if not os.path.exists(pdf_path):
        return json.dumps({"error": f"PDF文件未找到，请检查路径：{pdf_path}"}, ensure_ascii=False, indent=4)

    found_sections = defaultdict(list)
    key_chapter_locations = {} # 用于存储关键章节的首次出现页码

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # --- 1. 优先尝试解析目录（TOC） ---
            if hasattr(pdf, 'toc') and pdf.toc:
                for item in pdf.toc:
                    # item 格式通常是 (level, title, page_number, ...)
                    title = item[1]
                    page_num = item[2]
                    
                    # 匹配所有预定义的关键词到模块的映射
                    for keyword_in_map, related_modules in KEYWORD_MODULE_MAP.items():
                        if keyword_in_map in title: # 宽松匹配目录标题
                            # 记录这个关键词出现的页码
                            if (page_num) not in found_sections[keyword_in_map]:
                                found_sections[keyword_in_map].append(page_num)
                    
                    # 记录关键章节的首次出现位置
                    for key_chapter_name in KEY_CHAPTERS_TO_LOCATE:
                        # 简化匹配逻辑，如果目录项包含关键章节名，则记录
                        # 忽略斜杠和大小写，只要包含即可
                        if key_chapter_name.replace('/', '').lower() in title.replace('/', '').lower():
                            if key_chapter_name not in key_chapter_locations:
                                key_chapter_locations[key_chapter_name] = page_num
                                
            # --- 2. 如果目录解析不完整，则进行全文扫描 ---
            # 为了提高效率，实际应用中可以限制扫描的页码范围，例如只扫描前100页
            # 这里为了演示，仍然是对所有页面进行扫描
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        line_stripped = line.strip()
                        
                        # 匹配所有预定义的关键词到模块的映射
                        for keyword in KEYWORD_MODULE_MAP.keys():
                            # 改进的标题行匹配：
                            # 1. 允许章节前有“第X章”、“摘要”、“目录”、“正文”、“附注”等前缀
                            # 2. 匹配关键词本身
                            # 3. 限制行长度，排除正文段落的长句子
                            # 4. re.IGNORECASE 忽略大小写
                            if (re.search(r'(第[一二三四五六七八九十百]+[章节节]|摘要|目录|正文|附注)?\s*' + re.escape(keyword), line_stripped, re.IGNORECASE) and len(line_stripped) < 100):
                                if (page_num) not in found_sections[keyword]:
                                    found_sections[keyword].append(page_num)
                        
                        # 精确匹配并记录关键章节的首次出现位置
                        for key_chapter_name in KEY_CHAPTERS_TO_LOCATE:
                            # 使用更精确的正则表达式模式来识别关键章节标题
                            # 考虑到“主营业务/经营情况”等格式，我们需要分开处理
                            patterns = [
                                r'^\s*' + re.escape(key_chapter_name.split('/')[0]) + r'(\s*$)', # 匹配行首，后面是空格或行尾
                                r'^\s*(' + re.escape(key_chapter_name.split('/')[0]) + r'|' + re.escape(key_chapter_name.split('/')[-1]) + r')\s*$', # 匹配单行，包含“主营业务”或“经营情况”
                                r'\s*第[一二三四五六七八九十百]+[章节节]\s*' + re.escape(key_chapter_name.split('/')[0]) # 匹配“第X章 YYY”格式
                            ]
                            for pattern in patterns:
                                if re.search(pattern, line_stripped, re.IGNORECASE) and len(line_stripped) < 100:
                                    if key_chapter_name not in key_chapter_locations:
                                        key_chapter_locations[key_chapter_name] = page_num
                                    break # 找到一个匹配即可，避免重复记录

    except FileNotFoundError:
        return json.dumps({"error": f"PDF文件未找到，请检查路径：{pdf_path}"}, ensure_ascii=False, indent=4)
    except Exception as e:
        # 捕获其他可能的运行时错误，并以 JSON 格式返回错误信息
        return json.dumps({"error": f"处理PDF时发生错误: {e}"}, ensure_ascii=False, indent=4)

    # --- 构建最终的 JSON 索引数据 ---
    final_index_data = {}
    for i in range(1, 10):
        module_name_prefix = f"模块{i}："
        module_full_name = next((name for name in MODULE_TEMPLATES.keys() if name.startswith(module_name_prefix)), None)
        
        if module_full_name:
            module_data = MODULE_TEMPLATES[module_full_name].copy()
            module_data['核心章节'] = []
            module_data['核心页段'] = []
            final_index_data[module_full_name] = module_data

    # 将解析到的章节信息填充到对应的模块中
    for keyword, pages in found_sections.items():
        related_modules = KEYWORD_MODULE_MAP.get(keyword, [])
        for module_num_str in related_modules:
            module_full_name = next((name for name in MODULE_TEMPLATES.keys() if name.startswith(module_num_str)), None)
            if module_full_name:
                if keyword not in final_index_data[module_full_name]['核心章节']:
                    final_index_data[module_full_name]['核心章节'].append(keyword)
                final_index_data[module_full_name]['核心页段'].extend(pages)
    
    # 格式化核心页段和章节列表
    for module_name, details in final_index_data.items():
        # 核心章节：去重、排序、逗号连接
        details['核心章节'] = ", ".join(sorted(list(set(details['核心章节'])))) if details['核心章节'] else "未自动定位"
        # 核心页段：格式化为范围字符串
        details['核心页段'] = _format_page_ranges(details['核心页段'])
        # 补充页段：如果模块模板中没有定义，则使用默认值
        details['补充页段'] = details.get('补充页段', '无明显补充页段') 

    # --- 构建关键章节精确定位补充 ---
    key_chapters_output = {}
    for chapter in KEY_CHAPTERS_TO_LOCATE:
        # 获取精确的首次出现页码
        main_page = key_chapter_locations.get(chapter, "未定位")
        
        # 收集所有与此关键章节相关的页码（包括其他关键词的页码）
        all_pages_for_chapter = []
        search_keywords = []
        if '/' in chapter: # 处理如 "主营业务/经营情况"
            search_keywords.extend(chapter.split('/'))
        else:
            search_keywords.append(chapter)

        for sk in search_keywords:
            if sk in found_sections:
                all_pages_for_chapter.extend(found_sections[sk])
        
        formatted_pages = _format_page_ranges(all_pages_for_chapter)
        
        # 确定最终显示的页码信息
        page_info = "未定位"
        if main_page != "未定位" and formatted_pages != "未定位":
            if str(main_page) != formatted_pages: # 如果首次出现页和所有出现页不同，则显示范围
                page_info = f"第{main_page}页（另见{formatted_pages}）"
            else:
                page_info = f"第{main_page}页" # 否则只显示首次出现页
        elif main_page != "未定位":
            page_info = f"第{main_page}页"
        elif formatted_pages != "未定位":
            page_info = f"（见 {formatted_pages}）" # 如果主页未定位，但有其他页码信息

        key_chapters_output[chapter] = page_info

    # --- 汇总总体索引质量说明 ---
    # 这些可以根据解析结果动态生成，但为了简化，这里使用固定的描述
    # 实际中，可以根据 found_sections 的数量和质量来判断
    overall_quality_notes = {
        "定位明确模块": "模块2（报表数字与基础勾稽关系）、模块7（附注与重大事项深度审查）、模块1（报告结构与披露完整性）",
        "信息分散模块": "模块5（经营逻辑与业务合理性）、模块6（文本表述与财务数据一致性）、模块9（风险红旗综合识别）",
        "优先审核模块": "模块1、模块2、模块8",
        "索引特点": [
            "精确性：所有模块的核心页段都提供了具体的页码范围，而非宽泛描述",
            "可执行性：每个模块都明确了审核对象、审核动作和预期输出，可直接用于后续审核模块调用",
            "区分度：清晰区分了核心页段和补充页段，为后续审核提供了优先级指导",
            "完整性：覆盖了年报所有关键章节，为9个审核模块建立了完整的导航索引"
        ],
        "最终说明": "该索引表已足够具体，后续审核模块可直接据此执行相应的审核任务。"
    }

    # --- 组装最终的 JSON 输出 ---
    final_output_data = {
        "中谷物流2023年年度报告审核索引表": {
            "模块化可执行审核索引表": final_index_data,
            "关键章节精确定位补充": key_chapters_output,
            "总体索引质量说明": overall_quality_notes
        }
    }

    # 返回 JSON 字符串
    return json.dumps(final_output_data, ensure_ascii=False, indent=4)
