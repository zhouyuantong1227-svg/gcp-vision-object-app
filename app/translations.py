from __future__ import annotations

import re

GLOSSARY = {
    "2d barcode": "二维条码",
    "advertising": "广告",
    "airplane": "飞机",
    "animal": "动物",
    "architecture": "建筑",
    "art": "艺术",
    "barcode": "条形码",
    "billboard": "广告牌",
    "bird": "鸟",
    "book": "书籍",
    "brand": "品牌",
    "brochure": "宣传册",
    "building": "建筑",
    "business": "商业",
    "car": "汽车",
    "cat": "猫",
    "city": "城市",
    "clothing": "服饰",
    "computer": "电脑",
    "conference": "会议",
    "crowd": "人群",
    "cup": "杯子",
    "design": "设计",
    "display device": "显示设备",
    "document": "文档",
    "dog": "狗",
    "event": "活动",
    "face": "人脸",
    "flyer": "宣传单",
    "font": "字体",
    "food": "食物",
    "furniture": "家具",
    "graphic design": "平面设计",
    "human": "人物",
    "image": "图片",
    "illustration": "插画",
    "indoor": "室内",
    "laptop": "笔记本电脑",
    "logo": "标志",
    "machine": "设备",
    "mobile phone": "手机",
    "motor vehicle": "机动车",
    "motorcycle": "摩托车",
    "office": "办公室",
    "paper": "纸张",
    "people": "人物",
    "person": "人物",
    "poster": "海报",
    "presentation": "展示页",
    "product": "产品",
    "qr code": "二维码",
    "screenshot": "截图",
    "screen": "屏幕",
    "technology": "技术",
    "text": "文字",
    "tourism": "旅游",
    "train": "火车",
    "transport": "交通工具",
    "vehicle": "车辆",
    "web page": "网页",
    "window": "窗口",
}

TOKEN_GLOSSARY = {
    "2d": "二维",
    "advertising": "广告",
    "barcode": "条码",
    "book": "书籍",
    "business": "商业",
    "car": "汽车",
    "cat": "猫",
    "city": "城市",
    "code": "码",
    "computer": "电脑",
    "conference": "会议",
    "design": "设计",
    "dog": "狗",
    "event": "活动",
    "font": "字体",
    "graphic": "图形",
    "image": "图像",
    "indoor": "室内",
    "laptop": "笔记本",
    "logo": "标志",
    "mobile": "移动",
    "page": "页面",
    "paper": "纸张",
    "person": "人物",
    "poster": "海报",
    "presentation": "展示",
    "product": "产品",
    "qr": "二维码",
    "screen": "屏幕",
    "screenshot": "截图",
    "technology": "技术",
    "text": "文字",
    "vehicle": "车辆",
    "web": "网页",
}


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _normalize_key(text: str) -> str:
    normalized = re.sub(r"[-_/]+", " ", text.strip().casefold())
    return " ".join(normalized.split())


def translate_label(text: str) -> str:
    if not text:
        return text
    if _contains_chinese(text):
        return text

    key = _normalize_key(text)
    if key in GLOSSARY:
        return GLOSSARY[key]

    singular = key[:-1] if key.endswith("s") else key
    if singular in GLOSSARY:
        return GLOSSARY[singular]

    translated_tokens: list[str] = []
    changed = False
    for token in key.split():
        translated = TOKEN_GLOSSARY.get(token)
        if translated:
            translated_tokens.append(translated)
            changed = True
        else:
            translated_tokens.append(token.title())

    if changed:
        return " ".join(translated_tokens)
    return text
