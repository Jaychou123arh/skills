import pdfplumber
import re
import json
import os


# ===========================
# 一级章节（目录可识别）
# ===========================

MAIN_SECTIONS = {
    "释义": ["释义"],
    "公司简介和主要财务指标": ["公司简介"],
    "管理层讨论与分析": ["管理层讨论与分析"],
    "公司治理": ["公司治理"],
    "环境与社会责任": ["环境与社会责任"],
    "重要事项": ["重要事项", "重大事项"],
    "股份变动及股东情况": ["股份变动"],
    "财务报告": ["财务报告"]
}


# ===========================
# 财务报告内部结构（必须正文扫描）
# ===========================

FINANCIAL_STATEMENTS = {
    "审计报告": ["审计报告"],
    "合并资产负债表": ["合并资产负债表"],
    "母公司资产负债表": ["母公司资产负债表"],
    "合并利润表": ["合并利润表"],
    "母公司利润表": ["母公司利润表"],
    "合并现金流量表": ["合并现金流量表"],
    "母公司现金流量表": ["母公司现金流量表"],
    "合并所有者权益变动表": ["合并所有者权益变动表"],
    "母公司所有者权益变动表": ["母公司所有者权益变动表"],
    "财务报表附注": ["财务报表附注", "附注"]
}


# ===========================
# 解析目录页
# ===========================

def _parse_toc(pdf):
    toc_data = {}
    toc_pattern = re.compile(r'(.+?)\.{2,}\s*(\d+)$')

    for i in range(min(15, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        if "目录" not in text:
            continue

        for line in text.split("\n"):
            line = line.strip()
            match = toc_pattern.search(line)
            if match:
                name = match.group(1).strip()
                page = int(match.group(2))
                toc_data[name] = page

    return toc_data


def _match_main_sections(toc_data):
    results = {}
    for std_name, keywords in MAIN_SECTIONS.items():
        for toc_name, page in toc_data.items():
            if any(kw in toc_name for kw in keywords):
                results[std_name] = page
                break
    return results


def _build_ranges(start_dict, total_pages):
    sorted_items = sorted(start_dict.items(), key=lambda x: x[1])
    ranges = {}

    for i, (name, start) in enumerate(sorted_items):
        if i + 1 < len(sorted_items):
            end = sorted_items[i + 1][1] - 1
        else:
            end = total_pages

        ranges[name] = {
            "start_page": start,
            "end_page": end,
            "page_range": f"{start}-{end}" if start != end else str(start)
        }

    return ranges


# ===========================
# 财务报告内部扫描
# ===========================

def _detect_financial_statements(pdf, finance_start_page):
    found = {}

    for i in range(finance_start_page - 1, len(pdf.pages)):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        lines = text.split("\n")[:20]

        for name, keywords in FINANCIAL_STATEMENTS.items():
            if name in found:
                continue

            for kw in keywords:
                if any(kw in line for line in lines):
                    found[name] = i + 1
                    break

    return found


# ===========================
# 主函数
# ===========================

def generate_audit_index_from_pdf(pdf_path: str) -> str:

    if not os.path.exists(pdf_path):
        return json.dumps({"error": "文件不存在"}, ensure_ascii=False)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            # 1️⃣ 解析目录
            toc_data = _parse_toc(pdf)
            main_starts = _match_main_sections(toc_data)
            main_ranges = _build_ranges(main_starts, total_pages)

            # 2️⃣ 识别财务报告内部结构
            financial_ranges = {}

            if "财务报告" in main_ranges:
                finance_start = main_ranges["财务报告"]["start_page"]

                finance_starts = _detect_financial_statements(
                    pdf,
                    finance_start
                )

                finance_ranges = _build_ranges(
                    finance_starts,
                    total_pages
                )

                financial_ranges = finance_ranges

    except Exception as e:
        return json.dumps(
            {"error": f"PDF处理失败: {str(e)}"},
            ensure_ascii=False
        )

    result = {
        "文件信息": {
            "总页数": total_pages
        },
        "一级章节定位": main_ranges,
        "财务报告内部结构": financial_ranges
    }

    return json.dumps(result, ensure_ascii=False, indent=4)
