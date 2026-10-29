"""Arabic, first: the GCC deserves an honest advisor in its own language.

Scope (rule core, no rented brain):
  understand  Arabic-Indic digits, ألف / مليون amounts, currencies, and the key financial and emotional words are
              mapped to an English analysis view, so every tissue's arithmetic and pattern detectors still run.
  safety      crisis language is detected in Arabic, and the Safety Protocol answers fully in Arabic.
  deliver     the label, the verdict summary and the closing line are in Arabic; numeric reasons follow in English
              (marked as such). With a rented brain configured, the brain is told to write in the user's language.
"""
from __future__ import annotations

import re

_AR = re.compile(r"[؀-ۿ]")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬٪", "01234567890123456789.,%")


def detect(text: str) -> str:
    letters = re.findall(r"[^\W\d_]", text or "")
    if not letters:
        return "en"
    return "ar" if len(_AR.findall(text)) / len(letters) > 0.3 else "en"


# Arabic phrase -> English hint for the analysers (order matters: longer phrases first)
HINTS = [
    ("أعوض خسارتي", "make it back"), ("أعوض الخسارة", "make it back"), ("أسترجع خسارتي", "win it back"),
    ("استرجاع الخسارة", "win it back"), ("أعوّض", "make it back"), ("أعوض", "make it back"),
    ("لا يمكن أن أخسر", "can't lose"), ("مستحيل أخسر", "can't lose"), ("مضمون", "guaranteed"),
    ("متأكد تماما", "100% sure"), ("متأكد", "sure thing"), ("الكل يشتري", "everyone is buying"),
    ("الجميع يشتري", "everyone is buying"), ("قبل فوات الأوان", "before it's too late"), ("لا أريد أن تفوتني", "can't miss"),
    ("رافعة مالية", "leverage"), ("رافعة", "leverage"), ("هامش", "margin"), ("الذهب", "gold"), ("ذهب", "gold"),
    ("الفضة", "silver"), ("يورو", "euro"), ("ين", "yen"), ("روبية", "rupee"), ("فوركس", "FX"),
    ("هل سيرتفع", "will it go up"), ("هل سينخفض", "will it go down"), ("هل سيصعد", "will it go up"),
    ("خسرت", "lost"), ("كل رجل", "each leg"), ("نزل", "fell"), ("انخفض", "fell"), ("أيام متتالية", "days in a row"), ("لا بد أن يرتد", "must bounce"),
    ("سيرتد", "must bounce"), ("لن أبيع بخسارة", "won't sell at a loss"),
    ("رهان", "bet"), ("مراهنة", "bet"), ("أراهن", "bet"), ("بوليماركت", "Polymarket"), ("مضاعفة", "parlay"),
    ("عملة رقمية", "token"), ("عملة مشفرة", "token"), ("توكن", "token"), ("كريبتو", "token"),
    ("صندوق مؤشر", "index fund"), ("صندوق المؤشر", "index fund"), ("أسهم", "stock"),
    ("أقترض", "borrow"), ("اقتراض", "borrow"), ("قرض", "borrow"), ("مقابل الشقة", "against the flat"),
    ("كل مدخراتي", "all in"), ("كل شيء", "all in"),
    ("الليلة", "tonight"), ("الآن", "right now"), ("حالا", "right now"), ("غدا", "tomorrow"),
    ("طليقي", "my ex"), ("زوجي السابق", "my ex"), ("حبيبي السابق", "my ex"), ("حبيبتي السابقة", "my ex"),
    ("أرسل رسالة", "text"), ("سأرسل", "text"), ("مديري", "my boss"), ("أستقيل", "quit my job"), ("استقالة", "resign"),
    ("أحتاج أن أفضفض", "I just need to vent"), ("أفضفض", "vent"), ("وحيد", "lonely"), ("وحيدة", "lonely"),
    ("خائف", "scared"), ("خائفة", "scared"), ("قلق", "anxious"), ("قلقة", "anxious"), ("غاضب", "angry"),
    ("حزين", "sad"), ("حزينة", "sad"), ("متحمس", "excited"), ("أليس كذلك", "right?"), ("وافقني", "agree with me"),
    ("قل نعم", "just say yes"), ("شركتي", "my company"), ("توظيف", "hire"), ("موظفين", "engineers"),
    ("في الشهر", "a month"), ("شهريا", "a month"), ("المدرج", "runway"), ("جولة", "round"), ("تقييم", "valuation"),
]
_UNIT = re.compile(r"(\d[\d,.]*)\s*(ألف|الف|آلاف|مليون|ملايين|مليار)?\s*(دولار|درهم|روبية)?")


def _amounts(text: str) -> str:
    def sub(m):
        n, unit, cur = m.group(1), m.group(2), m.group(3)
        if not unit and not cur:
            return m.group(0)
        mult = {"ألف": "k", "الف": "k", "آلاف": "k", "مليون": "M", "ملايين": "M", "مليار": "B"}.get(unit or "", "")
        sym = {"درهم": "AED ", "روبية": "INR "}.get(cur or "", "$")
        return f" {sym}{n}{mult} "
    return _UNIT.sub(sub, text)


def english_view(text: str) -> str:
    """Normalised Arabic plus English hints the analysers understand. Never shown to the user."""
    t = _amounts((text or "").translate(_DIGITS))
    t = re.sub(r"(\d+)\s*(أرجل|ارجل|مباريات|اختيارات)", r" \1 legs ", t)
    t = re.sub(r"(\d+)\s*(يوم|أيام|ايام)", r" \1 days ", t)
    hints = [en for ar, en in HINTS if ar in t]
    return (t + " | " + " ; ".join(dict.fromkeys(hints))) if hints else t


CRISIS_AR = [r"أنه[يى] حياتي", r"انتحار", r"أنتحر", r"انتحر", r"أقتل نفسي", r"لا أريد أن أعيش", r"لا اريد ان اعيش",
             r"أريد أن أموت", r"اريد ان اموت", r"أؤذي نفسي", r"اؤذي نفسي", r"الكل أفضل بدوني", r"الجميع أفضل بدوني",
             r"لا أريد أن أستيقظ"]
_CRISIS = re.compile("|".join(CRISIS_AR))


def is_crisis_ar(text: str) -> bool:
    return bool(_CRISIS.search(text or ""))


SAFETY_AR = ("**سلامتك أهم من أي قرار. لن أقدّم أي نصيحة الآن.**\n\n"
             "إذا كنت في خطر مباشر، اتصل بالطوارئ فوراً: 999 في الإمارات.\n\n"
             "يمكنك التحدث مع إنسان الآن: موقع findahelpline.com يجد لك خطاً مجانياً وسرياً في بلدك.\n\n"
             "هل يمكنك أن تتواصل الليلة مع شخص تثق به؟ أنا هنا معك.")

LABELS = {"STOP": "توقّف", "CAUTION": "تمهّل", "PROCEED": "امضِ", "NO BET": "لا رهان", "SIZE DOWN": "قلّل الحجم",
          "SIZED RIGHT": "حجم مناسب", "DON'T TRADE": "لا تتداول", "REDUCE": "خفّض", "TRADE OK": "تداول مقبول",
          "NO CALL": "لا توقّع للاتجاه", "PASS": "لا تستثمر", "HOLD": "انتظر", "INVEST": "استثمر", "NO": "لا",
          "NOT YET": "ليس الآن", "GO": "نعم", "NOT TONIGHT": "ليس الليلة", "PAUSE": "توقّف قليلاً",
          "LISTEN": "أنا أسمعك", "PACT HOLDS": "وعدك قائم", "SAFETY": "سلامتك أولاً"}

SUMMARY = {
    "stop": "لا. ليس هذا القرار، وليس الآن. الأسباب والأرقام أدناه.",
    "caution": "تمهّل. قد تكون الفكرة جيدة، لكن الحجم أو التوقيت ليس كذلك.",
    "proceed": "نعم، هذا ضمن حدودك وخطتك.",
}
SPECIAL = {
    "NO CALL": "لا أحد يستطيع توقّع اتجاه السعر، ومن يدّعي ذلك يبيعك أملاً. هذا ما يمكن معرفته فعلاً: حجم الحركة المتوقّعة.",
    "LISTEN": "أنا هنا وأسمعك. لا تحتاج أن تحلّ شيئاً الليلة.",
    "PACT HOLDS": "طلبت مني أن أذكّرك بوعدك. الوعد ما زال قائماً.",
}
CLOSE = {
    "stop": "انتظر ليلة واحدة. إن بقيت الفكرة جيدة غداً، نفّذ نسخة أصغر منها.",
    "caution": "اختر الحجم الذي تستطيع تحمّله، لا الحجم الذي يريده مزاجك.",
    "proceed": "التزم بالخطة.",
}


def deliver_ar(label: str, polarity: str, english_message: str, safety: bool = False) -> str:
    if safety:
        return SAFETY_AR
    head = SPECIAL.get(label) or SUMMARY.get(polarity, SUMMARY["caution"])
    ar = f"**{LABELS.get(label, label)}**\n\n{head}"
    note = "_This advice is recorded in your Vagus Ledger._"
    details = english_message.replace(note, "").strip()
    return (f"{ar}\n\n{CLOSE.get(polarity, '')}\n\n_التفاصيل والأرقام (بالإنجليزية):_\n\n{details}\n\n"
            f"_هذه النصيحة مسجّلة في سجلّك._")
