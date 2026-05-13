import pdfplumber
import json
import os
import re


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


# ===============================
# 工具函数
# ===============================

def _clean_number(text):
    text = text.replace(",", "").strip()
    try:
        return float(text)
    except:
        return None


def _detect_statement_title(line):
    for title in ALL_STATEMENT_TITLES:
        if title in line:
            return title
    return None


def _extract_numbers_from_line(line):
    return re.findall(r"-?\d[\d,]*\.?\d*", line)


# ===============================
# 核心解析逻辑（文本驱动）
# ===============================

def _parse_financial_section(pdf, start_page, end_page):

    results = {}
    current_statement = None
    current_unit = "未知"

    for page_index in range(start_page - 1, end_page):

        page = pdf.pages[page_index]
        text = page.extract_text() or ""

        lines = text.split("\n")

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # 检测报表标题
            detected = _detect_statement_title(line)
            if detected:
                current_statement = detected
                if current_statement not in results:
                    results[current_statement] = {
                        "单位": "未知",
                        "数据": {}
                    }
                continue

            if not current_statement:
                continue

            # 识别单位
            if "单位" in line:
                match = re.search(r"单位[:：]\s*([^\n]+)", line)
                if match:
                    current_unit = match.group(1).strip()
                    results[current_statement]["单位"] = current_unit
                continue

            # 识别金额行
            numbers = _extract_numbers_from_line(line)

            if len(numbers) >= 2:

                first_number = numbers[0]
                item_name = line.split(first_number)[0].strip()

                if len(item_name) < 2:
                    continue

                results[current_statement]["数据"][item_name] = {
                    "本期": _clean_number(numbers[0]),
                    "上期": _clean_number(numbers[1])
                }

            elif len(numbers) == 1:

                first_number = numbers[0]
                item_name = line.split(first_number)[0].strip()

                if len(item_name) < 2:
                    continue

                results[current_statement]["数据"][item_name] = {
                    "本期": _clean_number(numbers[0]),
                    "上期": None
                }

    # 添加项目数量
    for stmt in results:
        results[stmt]["项目数量"] = len(results[stmt]["数据"])

    return results


# ===============================
# 主函数
# ===============================

def extract_all_financial_statements(pdf_path: str,
                                     finance_start_page: int,
                                     finance_end_page: int) -> str:

    if not os.path.exists(pdf_path):
        return json.dumps({"error": "文件不存在"}, ensure_ascii=False)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            parsed = _parse_financial_section(
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
