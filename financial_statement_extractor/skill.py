import pdfplumber
import json
import os
import re


# 所有报表标题
ALL_STATEMENT_TITLES = [
    "合并资产负债表",
    "母公司资产负债表",
    "合并利润表",
    "母公司利润表",
    "合并现金流量表",
    "母公司现金流量表",
    "合并所有者权益变动表",
    "母公司所有者权益变动表"
]


# ==========================
# 工具函数
# ==========================

def _clean_number(value):
    if not value:
        return None
    value = str(value).replace(",", "").strip()
    try:
        return float(value)
    except:
        return None


def _is_number(text):
    if not text:
        return False
    text = str(text).replace(",", "").strip()
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", text))


def _detect_statement_title(text):
    lines = text.split("\n")[:20]
    for title in ALL_STATEMENT_TITLES:
        if any(title in line for line in lines):
            return title
    return None


# ==========================
# 核心解析逻辑（全量扫描）
# ==========================

def _parse_all_statements(pdf, start_page, end_page):

    results = {}
    current_statement = None
    current_unit = "未知"

    for page_index in range(start_page - 1, end_page):

        page = pdf.pages[page_index]
        text = page.extract_text() or ""

        # 识别报表标题
        detected_title = _detect_statement_title(text)
        if detected_title:
            current_statement = detected_title
            if current_statement not in results:
                results[current_statement] = {
                    "单位": "未知",
                    "数据": {}
                }

        if not current_statement:
            continue

        # 提取单位
        if "单位" in text:
            match = re.search(r"单位[:：]\s*([^\n]+)", text)
            if match:
                current_unit = match.group(1).strip()
                results[current_statement]["单位"] = current_unit

        # 提取表格
        tables = page.extract_tables()
        if not tables:
            continue

        for table in tables:
            for row in table:
                if not row:
                    continue

                row = [str(cell).strip() if cell else "" for cell in row]

                item_name = row[0]
                if not item_name:
                    continue

                if len(item_name) > 80:
                    continue

                numbers = [cell for cell in row[1:] if _is_number(cell)]

                if len(numbers) >= 2:
                    results[current_statement]["数据"][item_name] = {
                        "本期": _clean_number(numbers[0]),
                        "上期": _clean_number(numbers[1])
                    }
                elif len(numbers) == 1:
                    results[current_statement]["数据"][item_name] = {
                        "本期": _clean_number(numbers[0]),
                        "上期": None
                    }

    # 统计项目数量
    for stmt in results:
        results[stmt]["项目数量"] = len(results[stmt]["数据"])

    return results


# ==========================
# 主函数
# ==========================

def extract_all_financial_statements(pdf_path: str,
                                     finance_start_page: int,
                                     finance_end_page: int) -> str:

    if not os.path.exists(pdf_path):
        return json.dumps({"error": "文件不存在"}, ensure_ascii=False)

    if not finance_start_page or not finance_end_page:
        return json.dumps({"error": "未提供财务报告页码范围"}, ensure_ascii=False)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            parsed = _parse_all_statements(
                pdf,
                finance_start_page,
                finance_end_page
            )

    except Exception as e:
        return json.dumps(
            {"error": f"报表解析失败: {str(e)}"},
            ensure_ascii=False
        )

    return json.dumps(parsed, ensure_ascii=False, indent=4)
