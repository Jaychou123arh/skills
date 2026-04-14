import pdfplumber
import re
import json
import os


# 同义词扩充（解决关键词找不到的问题）
DISCLOSURE_CHECKLIST = [
    {
        "项目": "公司基本信息",
        "关键词": ["股票代码", "注册地址", "法定代表人", "公司简介", "基本情况"],
        "优先查找章节": "公司治理",
        "重要性": "必须披露"
    },
    {
        "项目": "审计报告",
        "关键词": ["审计报告", "独立审计师报告", "注册会计师"],
        "优先查找章节": "审计报告",
        "重要性": "必须披露"
    },
    {
        "项目": "审计意见类型",
        "关键词": ["无保留意见", "保留意见", "否定意见", "无法表示意见",
                  "标准无保留", "无保留审计意见"],
        "优先查找章节": "审计报告",
        "重要性": "必须披露"
    },
    {
        "项目": "关键审计事项",
        "关键词": ["关键审计事项", "关键审计matter", "重要审计事项"],
        "优先查找章节": "审计报告",
        "重要性": "必须披露"
    },
    {
        "项目": "风险因素",
        "关键词": ["风险提示", "风险因素", "主要风险", "经营风险", "风险管理"],
        "优先查找章节": "风险提示",
        "重要性": "必须披露"
    },
    {
        "项目": "重大事项",
        "关键词": ["重大事项", "重要事项", "重大事件", "重大合同"],
        "优先查找章节": "重大事项",
        "重要性": "必须披露"
    },
    {
        "项目": "关联交易",
        "关键词": ["关联交易", "关联方交易", "关联方关系"],
        "优先查找章节": "重大事项",
        "重要性": "必须披露"
    },
    {
        "项目": "对外担保",
        "关键词": ["对外担保", "担保情况", "担保金额", "为他人提供担保"],
        "优先查找章节": "重大事项",
        "重要性": "必须披露"
    },
    {
        "项目": "诉讼仲裁",
        "关键词": ["诉讼", "仲裁", "法律纠纷", "重大诉讼"],
        "优先查找章节": "重大事项",
        "重要性": "重要披露"
    },
    {
        "项目": "内部控制评价",
        "关键词": ["内部控制评价", "内控评价", "内部控制报告",
                  "内控有效性", "内部控制自我评价"],
        "优先查找章节": "内部控制",
        "重要性": "必须披露"
    },
    {
        "项目": "会计政策变更",
        "关键词": ["会计政策变更", "会计估计变更", "追溯调整",
                  "会计政策调整"],
        "优先查找章节": "财务报表附注",
        "重要性": "重要披露"
    }
]


def _parse_page_ranges(pages_str: str) -> list:
    """把 '2, 4, 28-29' 解析成页码列表"""
    pages = []
    if not pages_str or pages_str in ["未定位", "未自动定位"]:
        return pages
    
    # 处理分号分隔的多段范围
    for segment in re.split(r'[;；]', pages_str):
        for part in segment.split(','):
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


def _check_keyword_in_pages(
    pdf, pages: list, keywords: list, check_full_page: bool = False
) -> tuple:
    """
    在指定页码范围内查找关键词
    check_full_page=False时只检查页首10行（减少误命中）
    返回 (置信度, 找到页码, 命中关键词)
    """
    high_confidence_pages = []  # 页首命中
    low_confidence_pages = []   # 正文命中
    hit_keyword = ""
    
    total_pages = len(pdf.pages)
    check_pages = pages if pages else list(range(1, total_pages + 1))
    
    for page_num in check_pages:
        if page_num < 1 or page_num > total_pages:
            continue
        
        page = pdf.pages[page_num - 1]
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # 页首检查（前10行）
        header_text = '\n'.join(lines[:10])
        for kw in keywords:
            if kw in header_text:
                if page_num not in high_confidence_pages:
                    high_confidence_pages.append(page_num)
                hit_keyword = kw
                break
        
        # 全页检查
        if check_full_page:
            for kw in keywords:
                if kw in text and page_num not in high_confidence_pages:
                    if page_num not in low_confidence_pages:
                        low_confidence_pages.append(page_num)
                    if not hit_keyword:
                        hit_keyword = kw
    
    if high_confidence_pages:
        pages_str = ', '.join(map(str, sorted(high_confidence_pages)))
        return "高置信度", high_confidence_pages, f"✅ 已确认（第{pages_str}页页首命中关键词：{hit_keyword}）"
    elif low_confidence_pages:
        pages_str = ', '.join(map(str, sorted(low_confidence_pages)))
        return "中置信度", low_confidence_pages, f"⚠️ 疑似存在（第{pages_str}页正文中提及：{hit_keyword}，建议人工确认）"
    else:
        return "未命中", [], f"❌ 未自动识别（可能使用了其他表述，建议人工查阅）"


def check_report_structure(pdf_path: str, module_info: str) -> str:
    """
    模块1：报告结构与披露完整性检查
    """
    if not os.path.exists(pdf_path):
        return f"❌ 错误：PDF文件未找到：{pdf_path}"
    
    # 解析模块定位信息
    try:
        module_details = json.loads(module_info)
    except:
        module_details = {}
    
    results = []
    found_count = 0
    high_confidence_count = 0
    missing_items = []
    need_manual_review = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            
            for item in DISCLOSURE_CHECKLIST:
                # 优先在对应章节的页码范围内查找
                chapter_key = item["优先查找章节"]
                
                # 从module_info里获取该章节的页码范围
                chapter_pages_str = ""
                if isinstance(module_details, dict):
                    # 尝试从索引结果里找页码
                    for key, val in module_details.items():
                        if chapter_key in str(key):
                            if isinstance(val, dict):
                                chapter_pages_str = val.get("页码范围", "")
                            elif isinstance(val, str):
                                chapter_pages_str = val
                
                priority_pages = _parse_page_ranges(chapter_pages_str)
                
                # 第一轮：在优先章节里找（高置信度）
                confidence, found_pages, status = _check_keyword_in_pages(
                    pdf, priority_pages, item["关键词"], check_full_page=True
                )
                
                # 第二轮：如果没找到，扩大到全文（中置信度）
                if confidence == "未命中" and priority_pages:
                    confidence, found_pages, status = _check_keyword_in_pages(
                        pdf, [], item["关键词"], check_full_page=True
                    )
                    if confidence != "未命中":
                        status = status.replace("✅", "⚠️").replace(
                            "已确认", "全文发现（非预期章节）"
                        )
                
                if confidence in ["高置信度", "中置信度"]:
                    found_count += 1
                    if confidence == "高置信度":
                        high_confidence_count += 1
                else:
                    missing_items.append(item["项目"])
                
                if confidence == "中置信度":
                    need_manual_review.append(item["项目"])
                
                results.append({
                    "项目": item["项目"],
                    "重要性": item["重要性"],
                    "置信度": confidence,
                    "检查结论": status
                })
    
    except Exception as e:
        return f"❌ 处理出错：{str(e)}"
    
    # 计算完整度
    total = len(DISCLOSURE_CHECKLIST)
    completeness = found_count / total * 100
    
    if completeness >= 90 and high_confidence_count >= 8:
        overall = "✅ 完整"
        risk = "🟢 低风险"
    elif completeness >= 70:
        overall = "⚠️ 基本完整"
        risk = "🟡 中风险"
    else:
        overall = "❌ 存在明显缺漏"
        risk = "🔴 高风险"
    
    # 生成报告
    lines = []
    lines.append("=" * 55)
    lines.append("📋 模块1：报告结构与披露完整性 审核结果")
    lines.append("=" * 55)
    lines.append("")
    lines.append("## 逐项检查结果")
    lines.append("")
    
    for r in results:
        lines.append(f"**{r['项目']}** [{r['重要性']}]")
        lines.append(f"  {r['检查结论']}")
        lines.append("")
    
    lines.append("=" * 55)
    lines.append("## 📊 总体评价")
    lines.append(f"- 发现项目：{found_count}/{total}")
    lines.append(f"- 高置信度确认：{high_confidence_count}项")
    lines.append(f"- 完整度：{completeness:.1f}%")
    lines.append(f"- 总体评级：{overall}")
    lines.append(f"- 风险等级：{risk}")
    
    if missing_items:
        lines.append("")
        lines.append("## ❌ 未识别项目（建议人工核实）")
        for item in missing_items:
            lines.append(f"  - {item}")
    
    if need_manual_review:
        lines.append("")
        lines.append("## ⚠️ 中置信度项目（建议人工确认）")
        for item in need_manual_review:
            lines.append(f"  - {item}（自动识别位置可能不准确）")
    
    lines.append("")
    lines.append("## 💡 说明")
    lines.append("高置信度 = 在预期章节的页首找到关键词")
    lines.append("中置信度 = 在非预期位置或正文中找到")
    lines.append("未识别  = 可能使用了不同表述，建议人工查阅")
    
    return "\n".join(lines)
