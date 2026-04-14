import pdfplumber
import re
import json
import os
from collections import defaultdict

# ============================================================
# 配置区：同义词扩充（解决"风险因素"找不到的问题）
# ============================================================
CHAPTER_SYNONYMS = {
    "审计报告":       ["审计报告", "独立审计师报告", "审计意见"],
    "财务报表":       ["财务报表", "合并财务报表", "财务报告"],
    "资产负债表":     ["资产负债表", "合并资产负债表", "财务状况表"],
    "利润表":         ["利润表", "合并利润表", "损益表", "综合收益表"],
    "现金流量表":     ["现金流量表", "合并现金流量表"],
    "所有者权益变动表":["所有者权益变动表", "合并所有者权益变动表", "股东权益变动表"],
    "财务报表附注":   ["财务报表附注", "附注", "会计报表附注"],
    "管理层讨论与分析":["管理层讨论与分析", "经营情况讨论与分析", "管理层分析"],
    "风险提示":       ["风险提示", "风险因素", "主要风险", "风险管理"],
    "重大事项":       ["重大事项", "重要事项", "重大事件"],
    "公司治理":       ["公司治理", "治理结构", "公司治理报告"],
    "内部控制":       ["内部控制", "内控评价", "内部控制评价报告"],
    "主营业务":       ["主营业务", "经营情况", "业务概要", "主要业务"],
    "股份变动":       ["股份变动", "股东情况", "股本变动"]
}

# 模块与章节的映射关系
MODULE_CHAPTER_MAP = {
    "模块1：报告结构与披露完整性": [
        "审计报告", "重大事项", "公司治理", "内部控制", "风险提示"
    ],
    "模块2：报表数字与基础勾稽关系": [
        "资产负债表", "利润表", "现金流量表", "所有者权益变动表", "财务报表"
    ],
    "模块3：盈利质量与现金流真实性": [
        "利润表", "现金流量表", "管理层讨论与分析"
    ],
    "模块4：债务、流动性与持续经营风险": [
        "资产负债表", "财务报表附注", "风险提示"
    ],
    "模块5：经营逻辑与业务合理性": [
        "管理层讨论与分析", "主营业务"
    ],
    "模块6：文本表述与财务数据一致性": [
        "管理层讨论与分析", "财务报表"
    ],
    "模块7：附注与重大事项深度审查": [
        "财务报表附注", "重大事项"
    ],
    "模块8：治理、合规与审计信号": [
        "审计报告", "公司治理", "内部控制", "股份变动"
    ],
    "模块9：风险红旗综合识别": [
        "风险提示", "重大事项", "财务报表附注"
    ]
}

MODULE_TEMPLATES = {
    "模块1：报告结构与披露完整性": {
        "审核对象": "审计意见类型、关键审计事项、关联交易披露、公司治理结构、内部控制评价",
        "审核动作": "提取、核对、对照、一致性审查",
        "预期输出": "披露项目清单、披露完整性评估、治理结构合规性清单"
    },
    "模块2：报表数字与基础勾稽关系": {
        "审核对象": "资产负债表平衡关系、利润表勾稽、现金流量表、三表间勾稽关系",
        "审核动作": "提取、计算、勾稽检查、核对",
        "预期输出": "勾稽异常项列表、报表平衡性验证结果"
    },
    "模块3：盈利质量与现金流真实性": {
        "审核对象": "净利润、经营现金流、应收账款、存货、毛利率",
        "审核动作": "提取、计算、对照、分析",
        "预期输出": "现金流真实性判断、盈利质量评估"
    },
    "模块4：债务、流动性与持续经营风险": {
        "审核对象": "资产负债率、流动比率、速动比率、有息负债、担保",
        "审核动作": "提取、计算、核对、红旗识别",
        "预期输出": "债务风险清单、流动性风险评估"
    },
    "模块5：经营逻辑与业务合理性": {
        "审核对象": "业务模式、市场环境、竞争优势、客户集中度",
        "审核动作": "提取、对照、一致性审查、逻辑验证",
        "预期输出": "业务逻辑合理性评估、异常波动清单"
    },
    "模块6：文本表述与财务数据一致性": {
        "审核对象": "业绩描述、盈利能力表述、现金流描述",
        "审核动作": "提取、核对、对照、一致性审查",
        "预期输出": "文本—数据偏差清单、表述准确性评估"
    },
    "模块7：附注与重大事项深度审查": {
        "审核对象": "关联交易、担保、诉讼、减值、会计政策变更",
        "审核动作": "提取、核对、深度分析、风险识别",
        "预期输出": "附注风险事项清单、重大事项影响评估"
    },
    "模块8：治理、合规与审计信号": {
        "审核对象": "审计意见、内控缺陷、董监高变动、监管处罚",
        "审核动作": "提取、核对、红旗识别、合规检查",
        "预期输出": "治理合规风险清单、审计信号分析"
    },
    "模块9：风险红旗综合识别": {
        "审核对象": "经营风险、财务风险、合规风险、行业风险",
        "审核动作": "提取、识别、分类、评估",
        "预期输出": "风险红旗清单、风险等级评估"
    }
}

# 跨页表格特征词（用于自动扩展）
TABLE_CONTINUATION_KEYWORDS = [
    "项目", "本期金额", "上期金额", "附注",
    "本年金额", "上年金额", "期末余额", "期初余额",
    "合计", "小计", "一、", "二、", "三、"
]


# ============================================================
# 核心函数1：解析目录页（最重要的改进）
# ============================================================
def _parse_toc_from_pdf(pdf) -> dict:
    """
    从PDF前10页里找目录页，
    用正则解析出"章节名 + 页码"
    返回 {章节名: 起始页码}
    """
    toc_data = {}
    
    # 目录页正则：匹配 "章节名称...123" 或 "章节名称 123"
    toc_pattern = re.compile(
        r'([^\d\n]{4,30}?)'      # 章节名（4-30个非数字字符）
        r'[\s\.…·\-]{0,20}'      # 分隔符（点线空格等）
        r'(\d{1,4})'             # 页码（1-4位数字）
        r'\s*$',                 # 行尾
        re.MULTILINE
    )
    
    # 只扫描前10页
    scan_pages = min(10, len(pdf.pages))
    
    for i in range(scan_pages):
        page = pdf.pages[i]
        text = page.extract_text()
        if not text:
            continue
        
        # 判断是否是目录页
        if "目录" not in text and "CONTENTS" not in text.upper():
            continue
        
        # 在目录页里提取章节和页码
        for line in text.split('\n'):
            line = line.strip()
            match = toc_pattern.search(line)
            if match:
                chapter_name = match.group(1).strip()
                page_num = int(match.group(2))
                
                # 过滤太短或无意义的匹配
                if len(chapter_name) >= 4 and page_num > 0:
                    toc_data[chapter_name] = page_num
    
    return toc_data


# ============================================================
# 核心函数2：把目录数据匹配到标准章节名
# ============================================================
def _match_toc_to_standard_chapters(toc_data: dict) -> dict:
    """
    把目录解析出的章节名
    匹配到我们预定义的标准章节名（含同义词）
    返回 {标准章节名: 起始页码}
    """
    matched = {}
    
    for standard_name, synonyms in CHAPTER_SYNONYMS.items():
        for toc_name, toc_page in toc_data.items():
            for synonym in synonyms:
                if synonym in toc_name or toc_name in synonym:
                    if standard_name not in matched:
                        matched[standard_name] = toc_page
                    break
    
    return matched


# ============================================================
# 核心函数3：全文扫描补充（目录解析失败时的备用）
# ============================================================
def _scan_pdf_for_chapters(pdf) -> dict:
    """
    备用方案：扫描全文找章节标题
    只看每页前10行，减少误命中
    """
    found = {}
    
    for i, page in enumerate(pdf.pages):
        page_num = i + 1
        text = page.extract_text()
        if not text:
            continue
        
        # 只看前10行（改进2：减少误命中）
        lines = text.split('\n')[:10]
        
        for line in lines:
            line = line.strip()
            if len(line) > 50:  # 标题不会太长
                continue
            
            for standard_name, synonyms in CHAPTER_SYNONYMS.items():
                if standard_name in found:
                    continue
                for synonym in synonyms:
                    if synonym in line:
                        found[standard_name] = page_num
                        break
    
    return found


# ============================================================
# 核心函数4：生成章节起止范围（替代散点页码）
# ============================================================
def _build_chapter_ranges(chapter_starts: dict, total_pages: int) -> dict:
    """
    根据各章节起始页，推算结束页
    结束页 = 下一章节起始页 - 1
    """
    if not chapter_starts:
        return {}
    
    # 按页码排序
    sorted_chapters = sorted(
        chapter_starts.items(),
        key=lambda x: x[1]
    )
    
    ranges = {}
    for idx, (name, start) in enumerate(sorted_chapters):
        if idx + 1 < len(sorted_chapters):
            end = sorted_chapters[idx + 1][1] - 1
        else:
            end = total_pages
        
        ranges[name] = {
            "起始页": start,
            "结束页": end,
            "页码范围": f"{start}-{end}" if start != end else str(start),
            "定位方式": "目录解析" if name in chapter_starts else "全文扫描"
        }
    
    return ranges


# ============================================================
# 核心函数5：跨页表格扩展
# ============================================================
def _extend_table_pages(pdf, start_page: int, end_page: int) -> int:
    """
    从start_page开始，检查后续页是否是表格延续
    如果是，扩展end_page
    用于解决跨页表格识别不全的问题
    """
    total = len(pdf.pages)
    extended_end = end_page
    
    for pg in range(end_page + 1, min(end_page + 5, total + 1)):
        page = pdf.pages[pg - 1]
        text = page.extract_text() or ""
        
        # 检查是否有表格延续特征
        continuation_count = sum(
            1 for kw in TABLE_CONTINUATION_KEYWORDS
            if kw in text
        )
        
        if continuation_count >= 2:  # 至少有2个特征词才算延续
            extended_end = pg
        else:
            break
    
    return extended_end


# ============================================================
# 主函数：生成审核索引
# ============================================================
def generate_audit_index_from_pdf(pdf_path: str) -> str:
    """
    主入口函数
    读取PDF → 解析目录 → 生成章节范围 → 构建模块索引
    """
    if not os.path.exists(pdf_path):
        return json.dumps(
            {"error": f"文件未找到：{pdf_path}"},
            ensure_ascii=False, indent=4
        )
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            # ① 优先用目录页解析
            toc_raw = _parse_toc_from_pdf(pdf)
            chapter_starts = _match_toc_to_standard_chapters(toc_raw)
            toc_source = "目录页解析"
            
            # ② 目录解析结果太少，用全文扫描补充
            if len(chapter_starts) < 5:
                scanned = _scan_pdf_for_chapters(pdf)
                for k, v in scanned.items():
                    if k not in chapter_starts:
                        chapter_starts[k] = v
                toc_source = "目录页解析+全文扫描补充"
            
            # ③ 生成章节起止范围
            chapter_ranges = _build_chapter_ranges(chapter_starts, total_pages)
            
            # ④ 对财务报表类章节做跨页扩展
            table_chapters = ["资产负债表", "利润表", "现金流量表", "所有者权益变动表"]
            for ch in table_chapters:
                if ch in chapter_ranges:
                    original_end = chapter_ranges[ch]["结束页"]
                    extended_end = _extend_table_pages(
                        pdf,
                        chapter_ranges[ch]["起始页"],
                        original_end
                    )
                    if extended_end > original_end:
                        chapter_ranges[ch]["结束页"] = extended_end
                        chapter_ranges[ch]["页码范围"] = (
                            f"{chapter_ranges[ch]['起始页']}-{extended_end}"
                        )
                        chapter_ranges[ch]["跨页扩展"] = f"已扩展至第{extended_end}页"
    
    except Exception as e:
        return json.dumps(
            {"error": f"处理PDF出错: {str(e)}"},
            ensure_ascii=False, indent=4
        )
    
    # ⑤ 构建9个模块的索引
    module_index = {}
    for module_name, chapter_list in MODULE_CHAPTER_MAP.items():
        core_chapters = []
        page_ranges = []
        confidence_notes = []
        
        for ch in chapter_list:
            if ch in chapter_ranges:
                info = chapter_ranges[ch]
                core_chapters.append(ch)
                page_ranges.append(info["页码范围"])
                confidence_notes.append(
                    f"{ch}（{info['页码范围']}页）"
                )
        
        template = MODULE_TEMPLATES.get(module_name, {})
        module_index[module_name] = {
            "核心章节": "、".join(core_chapters) if core_chapters else "未定位",
            "核心页段": "；".join(page_ranges) if page_ranges else "未定位",
            "置信度说明": "、".join(confidence_notes) if confidence_notes else "未自动定位，需人工确认",
            "审核对象": template.get("审核对象", ""),
            "审核动作": template.get("审核动作", ""),
            "预期输出": template.get("预期输出", "")
        }
    
    # ⑥ 关键章节精确定位
    key_chapters_output = {}
    for ch_name, info in chapter_ranges.items():
        key_chapters_output[ch_name] = {
            "页码范围": info["页码范围"],
            "起始页": info["起始页"],
            "结束页": info["结束页"],
            "定位方式": info.get("定位方式", "未知")
        }
    
    # ⑦ 组装最终输出
    result = {
        "文件信息": {
            "总页数": total_pages,
            "定位方式": toc_source,
            "识别章节数": len(chapter_ranges)
        },
        "关键章节定位": key_chapters_output,
        "模块化审核索引": module_index,
        "优先审核建议": {
            "第1优先": "模块1（报告结构与披露完整性）- 章节位置固定，可直接执行",
            "第2优先": "模块2（报表数字与基础勾稽关系）- 财务报表位置明确",
            "第3优先": "模块8（治理、合规与审计信号）- 审计报告位置固定"
        },
        "需人工校准模块": [
            "模块5（经营逻辑）- 业务描述分散",
            "模块6（文本一致性）- 需跨章节对照",
            "模块9（风险红旗）- 风险信息分散"
        ]
    }
    
    return json.dumps(result, ensure_ascii=False, indent=4)
