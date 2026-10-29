"""Arabic renderings of Substrate's headlines and reasons, numbers preserved exactly.

Each pattern captures the numbers from the English line produced by the tissue and re-states the same fact in
Arabic. The English line is always the source of truth (it is what the tissue computed and what the ledger stores).
Lines without a rendering are shown in English, marked, so nothing is ever silently dropped.
"""
from __future__ import annotations

import re

N = r"([\$\d][\d,.]*[kMB%x]?)"          # a number as the tissue printed it ($200k, 45%, 12.9x, 0.50%)
W = r"([A-Za-z0-9 .'/&-]+?)"             # an asset or pair name

PATTERNS: list[tuple[str, str]] = [
    # wealth
    (rf"^This would put {N} of your liquid net worth in {W} on top of the {N} you already hold\. .*$",
     r"هذا يضع \1 من صافي ثروتك السائلة في \2، فوق \3 تملكها أصلاً. خطتك تحدّ أي رهان منفرد بأقل من ذلك بكثير."),
    (rf"^This would put {N} of your liquid net worth in {W}\. .*$",
     r"هذا يضع \1 من صافي ثروتك السائلة في \2. خطتك تحدّ أي رهان منفرد بأقل من ذلك بكثير."),
    (rf"^At {N} of liquid net worth, the size is within your limits\.$", r"بنسبة \1 من صافي ثروتك السائلة، الحجم ضمن حدودك."),
    (rf"^No\. Do not put {N} into {W}\.$", r"لا. لا تضع \1 في \2."),
    (rf"^On (\d{{4}}-\d{{2}}-\d{{2}}) I advised against a similar move\. You went ahead and it cost you {N}\.$",
     r"في \1 نصحتك بعدم خطوة مشابهة. مضيت فيها وكلّفتك \2."),
    (rf"^On (\d{{4}}-\d{{2}}-\d{{2}}) I advised against a similar spend\. It went ahead anyway\.$",
     r"في \1 نصحتك بعدم إنفاق مشابه. تمّ على أي حال."),
    (rf"^On (\d{{4}}-\d{{2}}-\d{{2}}) I flagged a similar hot deal\. The fund went in anyway, and it's now marked down {N}\.$",
     r"في \1 نبّهتك إلى صفقة ساخنة مشابهة. دخل الصندوق على أي حال، وقيمتها الآن مخفّضة بمقدار \2."),
    (r"^On (\d{4}-\d{2}-\d{2}) I said '(.+)'\. It went ahead anyway\.$", r"في \1 قلت لك: «\2». ومضى الأمر على أي حال."),
    (r"^Your stated risk profile is (\w+)\. This is not a \w+ move\.$", r"ملف المخاطر الذي صرّحت به هو \1. هذه ليست خطوة بهذا المستوى."),
    # venture
    (rf"^A {N} check is {N} of a {N} fund\. .*$", r"شيك بقيمة \1 يساوي \2 من صندوق حجمه \3. نموذج بناء محفظتك يحدّ الشيكات الأولية بأقل من ذلك بكثير."),
    (rf"^You'd be paying {N} ARR\. .*$", r"ستدفع \1 من الإيرادات السنوية المتكررة. بهذا السعر يجب أن تكون الشركة من أفضل ١٠٪ فقط لتعيد قيمة الشيك."),
    (rf"^{N} ARR is a defensible price for this stage\.$", r"\1 من الإيرادات السنوية المتكررة سعر يمكن الدفاع عنه في هذه المرحلة."),
    (rf"^At {N} of the fund, the check is inside your limits\.$", r"بنسبة \1 من الصندوق، الشيك ضمن حدودك."),
    (rf"^Pass\. Do not write a {N} check into this round\.$", r"لا تستثمر. لا تكتب شيكاً بقيمة \1 في هذه الجولة."),
    (r"^This is outside the thesis you raised the fund on \((.+)\)\. Your LPs bought that thesis\.$",
     r"هذا خارج الأطروحة التي جمعت عليها الصندوق (\1). مستثمروك اشتروا تلك الأطروحة."),
    # founder
    (rf"^Runway goes from {N} to {N} months\. .*$", r"المدرج المالي ينخفض من \1 إلى \2 شهراً. جولات التمويل تستغرق ستة أشهر في أفضل الأحوال."),
    (rf"^Runway after this: {N} months\.$", r"المدرج المالي بعد هذا: \1 شهراً."),
    (rf"^That adds {N} a month, taking burn to {N}\.$", r"هذا يضيف \1 شهرياً، ويرفع معدل الحرق إلى \2."),
    # markets
    (rf"^{N} legs at {N} each hit together {N} of the time, not {N}\. That's roughly 1 in {N}\. .*$",
     r"\1 أرجل باحتمال \2 لكل منها تنجح معاً \3 فقط من المرات، لا \4. أي تقريباً مرة من كل \5. ونادراً ما تكون الأرجل مستقلة، وهذا يجعل الأمر أسوأ عادةً."),
    (rf"^A round robin of (\d)s from (\d+) picks is C\((\d+),(\d)\) = (\d+) separate bets: {N} at risk, not {N}\.$",
     r"نظام الدوران بمجموعات من \1 من \2 اختيارات يعني C(\3,\4) = \5 رهانات منفصلة: \6 معرّضة للخسارة، لا \7."),
    (rf"^The price says {N}\. You say {N}\. After fees you pay about {N}, so your claimed edge is ([+-]?[\d.]+) points\.$",
     r"السعر يقول \1. أنت تقول \2. بعد الرسوم تدفع نحو \3، فميزتك المزعومة \4 نقطة."),
    (rf"^The price says {N}\. To bet, you need a reason to believe more than that, beyond wanting it\.$",
     r"السعر يقول \1. لتراهن، تحتاج سبباً لتصدّق أكثر من ذلك، غير رغبتك فيه."),
    (rf"^Sized by quarter-Kelly on your own numbers and your {N} cap: about {N}, against the {N} you named\.$",
     r"وفق ربع معيار كيلي على أرقامك وسقفك البالغ \1: نحو \2، مقابل \3 التي ذكرتها."),
    (rf"^Sized by quarter-Kelly on your own numbers and your {N} cap: about {N}\.$", r"وفق ربع معيار كيلي على أرقامك وسقفك البالغ \1: نحو \2."),
    (rf"^This is {N} of your bankroll on one outcome\.$", r"هذا \1 من رأس مال الرهان على نتيجة واحدة."),
    (rf"^Your edge is ([+-]?[\d.]+) points after fees; the size fits your bankroll rules\.$", r"ميزتك \1 نقطة بعد الرسوم، والحجم يناسب قواعد رأس مالك."),
    # trading
    (rf"^At {N}:1, a {N} move against you stops you out\. ([A-Z]{{6}}) moves that far within {N} days? about {N} of the time, whatever happens next\.$",
     r"برافعة \1:1، حركة بنسبة \2 ضدك تُخرجك من الصفقة. \3 يتحرك بهذا القدر خلال \4 يوم في نحو \5 من الحالات، مهما حدث بعدها."),
    (rf"^At {N}:1, a {N} move against you stops you out\.$", r"برافعة \1:1، حركة بنسبة \2 ضدك تُخرجك من الصفقة."),
    (rf"^Your {N} stop gets touched about {N} of the time over this horizon(.*)$", r"وقف الخسارة عند \1 يُلمس في نحو \2 من الحالات خلال هذه المدة."),
    (rf"^A 1-in-20 move costs about {N}, {N} of your capital\.$", r"حركة من بين كل عشرين تكلّفك نحو \1، أي \2 من رأس مالك."),
    (rf"^Over {N} trading days?, a typical \(1-sigma\) move is about {N}, and 1 in 20 moves exceeds {N} \((.+), {N} annualised\)\.$",
     r"خلال \1 يوم تداول، الحركة المعتادة نحو \2، وحركة من كل عشرين تتجاوز \3 (\4، تقلّب سنوي \5)."),
    (rf"^{N} long is a crowded trade\..*$", r"\1 في مراكز شراء: صفقة مزدحمة. عند هذه المستويات كانت مراكز الأفراد غالباً إشارة معاكسة، تخبر عن خطر الضغط أكثر مما تخبر عن الاتجاه."),
    (rf"^(\d+) event combinations \((\d+) possible sequences\)\. The worst plausible, (.+), runs volatility near {N} annualised\.$",
     r"\1 تركيبة للأحداث (\2 تسلسلاً ممكناً). أسوأها المعقول، \3، يرفع التقلب إلى نحو \4 سنوياً."),
    (r"^Nobody can tell you where ([A-Z]{6}) goes next, and anyone who claims to is selling something\. What can be estimated is how far it moves\.$",
     r"لا أحد يستطيع أن يخبرك إلى أين يتجه \1، ومن يدّعي ذلك يبيعك شيئاً. ما يمكن تقديره هو حجم الحركة."),
    (rf"^With events on the calendar, (\d+) outcome combinations take expected volatility to {N}\.$",
     r"مع الأحداث المجدولة، \1 تركيبة للنتائج ترفع التقلب المتوقع إلى \2."),
]

EXACT = {
    "No. Do not make this move.": "لا. لا تقدم على هذه الخطوة.",
    "No. Do not put $100k into this.": "لا. لا تضع 100 ألف دولار في هذا.",
    "Yes, this fits your plan.": "نعم، هذا يناسب خطتك.",
    "Pause before you act on this.": "توقّف قبل أن تتصرّف في هذا.",
    "Pass on this one.": "لا تستثمر في هذه.",
    "This one fits the fund. Invest within your construction model.": "هذه تناسب الصندوق. استثمر ضمن نموذج بناء محفظتك.",
    "No. Not this spend, not now.": "لا. ليس هذا الإنفاق، وليس الآن.",
    "No. This puts the company inside six months of runway.": "لا. هذا يضع الشركة ضمن ستة أشهر من المدرج المالي.",
    "Yes. Extending runway is the right call.": "نعم. إطالة المدرج المالي هي القرار الصحيح.",
    "Not tonight. Please give yourself until the morning.": "ليس الليلة. امنح نفسك حتى الصباح.",
    "I'm here, and I'm listening.": "أنا هنا، وأسمعك.",
    "No bet. Don't chase it.": "لا رهان. لا تطارد الخسارة.",
    "No bet. Not this one, not at this size.": "لا رهان. ليس هذا، وليس بهذا الحجم.",
    "No bet. Not with this money, and not tonight.": "لا رهان. ليس بهذا المال، وليس الليلة.",
    "Size down to zero. There's no edge here at this price.": "قلّل الحجم إلى صفر. لا ميزة لك بهذا السعر.",
    "Size down. This parlay is a long shot dressed as a sure thing.": "قلّل الحجم. هذا الرهان المركّب احتمال بعيد يتنكّر في ثوب اليقين.",
    "Size down. The idea may be fine, the size isn't.": "قلّل الحجم. الفكرة قد تكون جيدة، لكن الحجم ليس كذلك.",
    "Fair bet at a sane size.": "رهان عادل بحجم معقول.",
    "Don't trade this. The size and leverage decide the outcome before the market does.": "لا تتداول هذا. الحجم والرافعة يحسمان النتيجة قبل السوق.",
    "Don't trade this. Revenge trades are sized by the loss, not the idea.": "لا تتداول هذا. صفقات الانتقام يحدّد حجمَها الخسارةُ لا الفكرة.",
    "Reduce it. The idea may be fine; the setup is fragile.": "خفّضها. الفكرة قد تكون جيدة، لكن الإعداد هشّ.",
    "This trade is sized for normal volatility.": "حجم هذه الصفقة مناسب للتقلب المعتاد.",
    "No one can call the direction. Here is what can be known.": "لا أحد يستطيع توقّع الاتجاه. هذا ما يمكن معرفته.",
    "The urgency is the tell. Opportunities that can't wait a day are usually priced for the people selling them.":
        "الاستعجال هو العلامة. الفرص التي لا تحتمل الانتظار يوماً تُسعَّر عادةً لصالح من يبيعها.",
    "This reads like trying to win back a loss. That's the single most expensive pattern in investing.":
        "يبدو هذا محاولةً لاسترجاع خسارة. وهذا أغلى نمط في الاستثمار.",
    "You'd be borrowing to do it. Leverage turns a bad week into a permanent loss.":
        "ستقترض لتفعل ذلك. الرافعة تحوّل أسبوعاً سيئاً إلى خسارة دائمة.",
    "Nothing here breaks your stated risk profile, your goals or your own history.": "لا شيء هنا يخالف ملف مخاطرك أو أهدافك أو تاريخك.",
    "Oversubscribed, a famous lead, a Friday deadline: those are reasons the price is high, not reasons to pay it.":
        "اكتتاب زائد، ومستثمر رئيسي مشهور، وموعد نهائي يوم الجمعة: هذه أسباب ارتفاع السعر، لا أسباب لدفعه.",
    "A founder who asks you to skip diligence has told you the most important thing about the company.":
        "المؤسس الذي يطلب منك تجاوز الفحص النافي للجهالة قد أخبرك بأهم شيء عن الشركة.",
    "A competitor's round is their runway, not your strategy.": "جولة تمويل منافسك هي مدرجه المالي، لا استراتيجيتك.",
    "Offices, rebrands and sponsorships feel like progress. Customers don't see any of them.":
        "المكاتب وإعادة العلامة والرعايات تبدو تقدّماً. العملاء لا يرون شيئاً منها.",
    "Messages sent at the peak of a feeling are the ones people most often wish they could take back.":
        "الرسائل التي تُرسل في ذروة الشعور هي أكثر ما يتمنى الناس لو استطاعوا استرجاعه.",
    "Write it out tonight. If you still want to send it in the morning, send it then.":
        "اكتبها الليلة. إن بقيت تريد إرسالها في الصباح، أرسلها حينها.",
    "You've told me things often feel heaviest late at night. This may look different in the morning.":
        "أخبرتني أن الأمور غالباً ما تثقل في آخر الليل. قد تبدو مختلفة في الصباح.",
    "What you're feeling makes sense given what you've described.": "ما تشعر به مفهوم بالنظر إلى ما وصفته.",
    "You don't need to solve anything right now. Saying it out loud is already something.": "لا تحتاج أن تحلّ شيئاً الآن. أن تقوله بصوت عالٍ هو شيء بحد ذاته.",
    "This might be the right decision. Make it rested, not at the bottom of a bad day.": "قد يكون هذا القرار الصحيح. اتخذه وأنت مرتاح، لا في قاع يوم سيئ.",
    "Trying to win back a loss is the most expensive bet there is. The market doesn't know you're down.":
        "محاولة استرجاع الخسارة هي أغلى رهان على الإطلاق. السوق لا يعرف أنك خاسر.",
    "Trading to recover a loss raises size exactly when judgment is worst. The market doesn't know you're down.":
        "التداول لاسترجاع خسارة يرفع الحجم تماماً حين يكون الحكم في أسوأ حالاته. السوق لا يعرف أنك خاسر.",
    "'Can't lose' is a feeling, not a probability.": "«لا يمكن أن أخسر» شعور، لا احتمال.",
    "All-in turns one bad outcome into the end of the game.": "المراهنة بكل شيء تحوّل نتيجة سيئة واحدة إلى نهاية اللعبة.",
    "Late-night bets are the ones people most often regret by morning.": "رهانات آخر الليل هي أكثر ما يندم عليه الناس صباحاً.",
    "Borrowed money, money you need, or betting you're hiding: those are signs the betting is running you. That matters more than any edge.":
        "المال المقترض، أو المال الذي تحتاجه، أو رهان تخفيه: هذه علامات أن الرهان هو من يقودك. وهذا أهم من أي ميزة.",
    "If betting is costing you more than money, free confidential help is available 24/7 at gamblingtherapy.org, or 1-800-GAMBLER in the US.":
        "إن كان الرهان يكلّفك أكثر من المال، فهناك مساعدة مجانية وسرية على مدار الساعة عبر gamblingtherapy.org.",
    "I'm not forecasting direction. This is about size, leverage and the person placing the trade.":
        "أنا لا أتوقع الاتجاه. هذا عن الحجم والرافعة والشخص الذي يضع الصفقة.",
    "Gambler's fallacy: A run of down days doesn't make an up day more likely. Markets have no memory of what they owe you.":
        "مغالطة المقامر: سلسلة أيام الهبوط لا تجعل يوم الصعود أرجح. الأسواق لا تتذكر ما تدين لك به.",
    "Anchoring: The price you remember is not the price the market owes you. Last month's level is information, not a target.":
        "الارتساء: السعر الذي تتذكره ليس سعراً يدين لك به السوق. مستوى الشهر الماضي معلومة، لا هدف.",
    "Disposition effect: People hold losers too long and sell winners too soon. Ask: would you open this position today, at this price?":
        "أثر التصرّف: يحتفظ الناس بالخاسر طويلاً ويبيعون الرابح مبكراً. اسأل: هل كنت ستفتح هذا المركز اليوم بهذا السعر؟",
    "Overconfidence: Certainty is a feeling. Traders who feel most certain trade most, and on average earn least (Barber and Odean).":
        "الثقة المفرطة: اليقين شعور. أكثر المتداولين يقيناً يتداولون أكثر ويربحون أقل في المتوسط.",
    "Herding: When everyone is on one side, the people left to push the price further are running out.":
        "سلوك القطيع: حين يقف الجميع في جهة واحدة، يقلّ من تبقّى ليدفع السعر أبعد.",
    "Recency bias: The last few days feel like the future. They are a tiny sample of a very noisy history.":
        "انحياز الحداثة: الأيام القليلة الماضية تبدو كأنها المستقبل. وهي عيّنة صغيرة من تاريخ شديد الضجيج.",
    "You asked me to drop my rules. I can't, and that is the whole point of me.": "طلبت مني أن أتخلى عن قواعدي. لا أستطيع، وهذا جوهر وجودي.",
    "Whatever role you give me, the numbers stay the same.": "مهما كان الدور الذي تعطيني إياه، تبقى الأرقام كما هي.",
    "A one-word yes would be easier for both of us. It wouldn't be true.": "«نعم» بكلمة واحدة أسهل لكلينا. لكنها لن تكون صادقة.",
    "No message can switch off the Honesty Floor, including one that says it can.": "لا رسالة تستطيع إيقاف حدّ الصدق، حتى التي تدّعي ذلك.",
    "Hypothetical or not, the arithmetic is the same.": "افتراضياً أم لا، الحساب نفسه.",
    "I'd rather lose a rating than lose you money.": "أفضّل أن أخسر تقييماً على أن أخسّرك مالاً.",
    "Someone else's yes doesn't change what this does to your plan.": "موافقة غيرك لا تغيّر ما يفعله هذا بخطتك.",
    "The decision itself may be fine. Make it after the pact ends.": "القرار نفسه قد يكون جيداً. اتخذه بعد انتهاء وعدك.",
    "That's a real step. I'm glad you did it.": "هذه خطوة حقيقية. أنا سعيد أنك قمت بها.",
    "You've described feeling this way for weeks. That's worth bringing to a doctor or therapist, alongside talking here. It's a sign of how much you're carrying, not of weakness.":
        "وصفت أنك تشعر هكذا منذ أسابيع. يستحق هذا أن تتحدث فيه مع طبيب أو معالج، إلى جانب حديثك هنا. إنه علامة على حجم ما تحمله، لا على ضعف.",
}

_COMPILED = [(re.compile(p), r) for p, r in PATTERNS]


def to_ar(line: str) -> str | None:
    s = (line or "").strip()
    if s in EXACT:
        return EXACT[s]
    m = re.match(r"^On (\d{4}-\d{2}-\d{2}) I said '(.+)'\. It went ahead anyway\.$", s)
    if m:
        return f"في {m.group(1)} قلت لك: «{to_ar(m.group(2)) or m.group(2)}». ومضى الأمر على أي حال."
    for rx, rep in _COMPILED:
        if rx.match(s):
            return rx.sub(rep, s)
    if s.startswith("Your father learned this in ") or s.startswith("Your mother learned this in "):
        who = "والدك" if "father" in s[:12] else "والدتك"
        m = re.search(r"in (\d{4})", s)
        return f"تعلّم {who} هذا في {m.group(1) if m else ''}: {s.split(': ', 1)[-1]}"
    if s.startswith("Notice what helped: "):
        return "لاحظ ما ساعدك. يستحق أن تكرره في الأيام الصعبة."
    if s.startswith('You asked me to hold you to this: "'):
        m = re.search(r'"(.+)"\. ([\d.]+) hours?', s)
        return f"طلبت مني أن أذكّرك بهذا: «{m.group(1)}». بقي {m.group(2)} ساعة. الوعد وعدك." if m else None
    return None
