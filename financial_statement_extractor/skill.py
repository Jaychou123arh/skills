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


# ===============================
# 判断是否是金额
# ===============================

def _is_number(text):
    if not text:
        return False
    text = str(text).replace(",", "")
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", text))


# ===============================
# 解析单张报表（完整逐行结构化）
# ===============================

def _parse_statement_tables(pdf, start_page, end_page):

    result = {}
    unit = "未知"

    for page_index in range(start_page - 1, end_page):
        page = pdf.pages[page_index]

        text = page.extract_text() or ""
        if "单位:" in text:
            unit_match = re.search(r"单位[:：]\s*([^\n]+)", text)
            if unit_match:
                unit = unit_match.group(1).strip()

        tables = page.extract_tables()

        if not tables:
            continue

        for table in tables:

            for row in table:
                if not row:
                    continue

                row = [str(cell).strip() if cell else "" for cell in row]

                # 第一列通常是项目名称
                item_name = row[0]

                if not item_name:
                    continue

                # 过滤明显无效行
                if len(item_name) > 50:
                    continue

                # 找数值列
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
        "数据": result
    }


# ===============================
# 主函数
# ===============================

def extract_full_financial_statements(pdf_path: str, statements_ranges: dict) -> str:

    if not os.path.exists(pdf_path):
        return json.dumps({"error": "文件不存在"}, ensure_ascii=False)

    all_results = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:

            for statement_name, page_info in statements_ranges.items():

                start_page = page_info["start_page"]
                end_page = page_info["end_page"]

                parsed = _parse_statement_tables(
                    pdf,
                    start_page,
                    end_page
                )

                all_results[statement_name] = {
                    "page_range": f"{start_page}-{end_page}",
                    "单位": parsed["单位"],
                    "项目数量": len(parsed["数据"]),
                    "数据": parsed["数据"]
                }

    except Exception as e:
        return json.dumps(
            {"error": f"处理失败: {str(e)}"},
            ensure_ascii=False
        )

    return json.dumps(all_results, ensure_ascii=False, indent=4)
