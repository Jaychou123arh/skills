import pdfplumber
import json
import os
import re


# ===============================
# 数值清洗
# ===============================

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


# ===============================
# 解析单张报表（完整逐行抽取）
# ===============================

def _parse_statement(pdf, start_page, end_page):

    result = {}
    unit = "未知"

    for page_index in range(start_page - 1, end_page):
        page = pdf.pages[page_index]

        text = page.extract_text() or ""

        # 提取单位
        if "单位" in text:
            match = re.search(r"单位[:：]\s*([^\n]+)", text)
            if match:
                unit = match.group(1).strip()

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

                if len(item_name) > 50:
                    continue

                numbers = [cell for cell in row[1:] if _is_number(cell)]

                if len(numbers) >= 2:
                    result[item_name] = {
                        "本期": _clean_number(numbers[0]),
                        "上期": _clean_number(numbers[1])
                    }
                elif len(numbers) == 1:
                    result[item_name] = {
                        "本期": _clean_number(numbers[0]),
                        "上期": None
                    }

    return {
        "单位": unit,
        "项目数量": len(result),
        "数据": result
    }


# ===============================
# 主函数（严格依赖技能1）
# ===============================

def extract_full_financial_statements(pdf_path: str, financial_structure: dict) -> str:

    if not os.path.exists(pdf_path):
        return json.dumps({"error": "文件不存在"}, ensure_ascii=False)

    if not financial_structure:
        return json.dumps({"error": "未提供财务报表结构数据"}, ensure_ascii=False)

    results = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:

            for statement_name, page_info in financial_structure.items():

                start_page = page_info.get("start_page")
                end_page = page_info.get("end_page")

                if not start_page or not end_page:
                    continue

                parsed = _parse_statement(
                    pdf,
                    start_page,
                    end_page
                )

                results[statement_name] = {
                    "page_range": f"{start_page}-{end_page}",
                    "单位": parsed["单位"],
                    "项目数量": parsed["项目数量"],
                    "数据": parsed["数据"]
                }

    except Exception as e:
        return json.dumps(
            {"error": f"报表解析失败: {str(e)}"},
            ensure_ascii=False
        )

    return json.dumps(results, ensure_ascii=False, indent=4)
