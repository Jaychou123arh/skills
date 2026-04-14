import pdfplumber
import re
import json
import os


def _parse_page_ranges(pages_str: str) -> list:
    """
    把 '2, 4, 28-29, 42' 这样的字符串
    解析成页码列表 [2, 4, 28, 29, 42]
    """
    pages = []
    if not pages_str or pages_str == "未定位":
        return pages
    
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = part.split('-')
                pages.extend(range(int(start.strip()), int(end.strip()) + 1))
            except:
                pass
        else:
            try:
                pages.append(int(part))
            except:
                pass
    return pages


def _check_keyword_in_pdf(pdf_path: str, pages: list, keywords: list) -> tuple:
    """
    在指定页码范围内查找关键词
    返回 (状态, 找到的页码列表)
    """
    found_pages = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            check_pages = pages if pages else list(range(1, len(pdf.pages) + 1))
            
            for page_num in check_pages:
                if page_num < 1 or page_num > len(pdf.pages):
                    continue
                    
                page = pdf.pages[page_num - 1]
                text = page.extract_text() or ""
                
                for kw in keywords:
                    if kw in text and page_num not in found_pages:
                        found_pages.append(page_num)
                        break
    except Exception as e:
        return f"检查出错: {str(e)}", []
    
    if found_pages:
        return f"✅ 已找到（第{', '.join(map(str, sorted(found_pages)))}页）", found_pages
    else:
        return "❌ 未找到", []


# 需要检查的披露项目清单
DISCLOSURE_CHECKLIST = [
    {
        "项目": "公司基本信息",
        "关键词": ["股票代码", "注册地址", "法定代表人", "公司简介"],
        "重要性": "必须披露"
    },
    {
        "项目": "审计报告",
        "关键词": ["审计报告", "注册会计师", "审计意见"],
        "重要性": "必须披露"
    },
    {
        "项目": "审计意见类型",
        "关键词": ["无保留意见", "保留意见", "否定意见", "无法表示意见", "标准无保留"],
        "重要性": "必须披露"
    },
    {
        "项目": "关键审计事项",
        "关键词": ["关键审计事项", "关键审计matter"],
        "重要性": "必须披露"
    },
    {
        "项目": "风险因素",
        "关键词": ["风险因素", "风险提示", "主要风险"],
        "重要性": "必须披露"
    },
    {
        "项目": "重大事项",
        "关键词": ["重大事项", "重要事项"],
        "重要性": "必须披露"
    },
    {
        "项目": "关联交易",
        "关键词": ["关联交易", "关联方交易"],
        "重要性": "必须披露"
    },
    {
        "项目": "对外担保",
        "关键词": ["对外担保", "担保情况", "担保金额"],
        "重要性": "必须披露"
    },
    {
        "项目": "诉讼仲裁",
        "关键词": ["诉讼", "仲裁", "法律纠纷"],
        "重要性": "重要披露"
    },
    {
        "项目": "内部控制评价",
        "关键词": ["内部控制评价", "内控评价", "内控报告"],
        "重要性": "必须披露"
    },
    {
        "项目": "会计政策变更",
        "关键词": ["会计政策变更", "会计估计变更", "追溯调整"],
        "重要性": "重要披露"
    }
]


def check_report_structure(pdf_path: str, module_info: str) -> str:
    """
    检查年报的报告结构与披露完整性。
    """
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        return f"❌ 错误：PDF文件未找到：{pdf_path}"

    # 解析模块定位信息
    try:
        module_details = json.loads(module_info)
        core_pages_str = module_details.get("核心页段", "")
        core_pages = _parse_page_ranges(core_pages_str)
    except json.JSONDecodeError:
        # 如果module_info不是有效JSON，就扫描全文
        core_pages = []
        module_details = {}

    # 开始检查
    results = []
    found_count = 0
    missing_items = []

    for item in DISCLOSURE_CHECKLIST:
        status, found_pages = _check_keyword_in_pdf(
            pdf_path, core_pages, item["关键词"]
        )
        
        if "✅" in status:
            found_count += 1
        else:
            missing_items.append(item["项目"])
        
        results.append({
            "项目": item["项目"],
            "重要性": item["重要性"],
            "检查结论": status
        })

    # 计算完整度
    total = len(DISCLOSURE_CHECKLIST)
    completeness_rate = found_count / total * 100

    if completeness_rate >= 90:
        overall = "✅ 完整"
        risk_level = "🟢 低风险"
    elif completeness_rate >= 70:
        overall = "⚠️ 基本完整"
        risk_level = "🟡 中风险"
    else:
        overall = "❌ 存在明显缺漏"
        risk_level = "🔴 高风险"

    # 生成报告
    report = []
    report.append("=" * 50)
    report.append("📋 模块1：报告结构与披露完整性 审核结果")
    report.append("=" * 50)
    report.append("")
    report.append("## 逐项检查结果")
    report.append("")
    
    for r in results:
        report.append(f"**{r['项目']}** [{r['重要性']}]")
        report.append(f"  → {r['检查结论']}")
        report.append("")

    report.append("=" * 50)
    report.append("## 📊 总体评价")
    report.append(f"- 完整项目：{found_count}/{total}")
    report.append(f"- 完整度：{completeness_rate:.1f}%")
    report.append(f"- 总体评级：{overall}")
    report.append(f"- 风险等级：{risk_level}")
    
    if missing_items:
        report.append("")
        report.append("## ⚠️ 缺失项目")
        for item in missing_items:
            report.append(f"  - {item}")
    
    report.append("")
    report.append("## 💡 建议")
    report.append("以上缺失项目需人工核实是否确实未披露，")
    report.append("或因关键词匹配未能自动识别，建议人工复核。")

    return "\n".join(report)
