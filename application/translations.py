import logging
from typing import Dict, Optional

from flask import request, session

logger = logging.getLogger(__name__)


TRANSLATIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "messages": {  # Error messages
        "invalid_vector": {
            "he": "הסכום חייב להיות 100 וכל מספר חייב להתחלק ב-5.",
            "en": "The sum must be 100 and each number must be divisible by 5.",
        },
        "total_not_100": {
            "he": "נא לוודא שהסכום הכולל הוא 100.",
            "en": "Please ensure the total sum is 100.",
        },
        "choose_all_pairs": {
            "he": "נא לבחור אפשרות אחת עבור כל זוג.",
            "en": "Please choose one option for each pair.",
        },
        "failed_awareness": {
            "he": "נכשלת בבדיקת הערנות. אנא נסה שוב ושים לב לשאלות.",
            "en": "Failed awareness check. Please try again and pay attention to the questions.",
        },
        "survey_processing_error": {
            "he": "אירעה שגיאה במהלך עיבוד הסקר. אנא נסה שוב.",
            "en": "An error occurred while processing the survey. Please try again.",
        },
        "missing_parameter": {
            "he": "פרמטר חסר: {param}",
            "en": "Missing parameter: {param}",
        },
        "survey_not_found": {"he": "הסקר לא נמצא", "en": "Survey not found"},
        "survey_no_subjects": {
            "he": "הסקר לא נמצא או אין לו נושאים",
            "en": "Survey not found or has no subjects",
        },
        "report_error": {
            "he": "אירעה שגיאה בהפקת הדוח. אנא נסה שוב מאוחר יותר.",
            "en": "An error occurred generating the report. Please try again later.",
        },
    },
    "survey": {  # Survey content
        "welcome": {"he": "ברוכים הבאים לסקר", "en": "Welcome to the Survey"},
        "intro_text": {
            "he": "נעים מאוד, אנו פרופ' אראל סגל-הלוי ופרופ' נועם חזון עורכים מחקר בנושא העדפות אזרחים לגבי חלוקת תקציב. המחקר נערך במסגרת המחלקה למדעי המחשב באוניברסיטת אריאל. אנו מזמינים אותך להשתתף במחקר שלנו על ידי מתן מענה על שאלון מקוון שאורכו כ-5 דקות.",
            "en": "Hello, we are Prof. Erel Segal-Halevi and Prof. Noam Hazon conducting research on citizens' preferences regarding budget allocation. The research is conducted at the Computer Science Department of Ariel University. We invite you to participate in our research by answering an online questionnaire that takes about 5 minutes.",
        },
        "what_to_expect": {
            "he": "מה מצפה לך בסקר?",
            "en": "What to expect in the survey?",
        },
        "survey_steps": {
            "he": [
                "תתבקש/י לחלק תקציב נתון בין מספר גופים שונים.",
                "לאחר מכן, תוצג בפניך סדרה של אפשרויות שונות לחלוקת תקציב.",
                "עבור כל זוג אפשרויות, תתבקש/י לבחור את האפשרות המועדפת עליך.",
            ],
            "en": [
                "You will be asked to allocate a given budget between different bodies.",
                "Then, you will be presented with a series of different budget allocation options.",
                "For each pair of options, you will be asked to choose your preferred option.",
            ],
        },
        "ideal_budget": {
            "he": "חלוקת התקציב האידיאלית לדעתך היא:",
            "en": "Your ideal budget allocation is:",
        },
        "reality_explanation": {
            "he": "אבל במציאות, חלוקת התקציב לא זהה לחלוקה האידיאלית שלך. בהמשך נציג לפניך עשרה זוגות של חלוקות-תקציב לא אידיאליות. עבור כל אחד מהזוגות, עליך לבחור איזו מבין שתי החלוקות טובה יותר בעיניך.",
            "en": "However, in reality, the budget allocation differs from your ideal allocation. We will present you with ten pairs of non-ideal budget allocations. For each pair, you need to choose which of the two allocations is better in your opinion.",
        },
        "pair": {"he": "זוג", "en": "Pair"},
        "option": {"he": "חלוקה", "en": "Option"},
        "awareness_check": {"he": "שאלת בדיקה", "en": "Awareness Check"},
        "awareness_question": {
            "he": "איזו מהאפשרויות הבאות מייצגת את התקציב האידיאלי שבחרת בתחילת הסקר?",
            "en": "Which of the following options represents the ideal budget you chose at the beginning of the survey?",
        },
        "comments": {"he": "הערות", "en": "Comments"},
        "submit": {"he": "שלח סקר", "en": "Submit Survey"},
        "thank_you": {
            "he": "תודה רבה על השתתפותך!",
            "en": "Thank you for your participation!",
        },
        "thank_you_message": {
            "he": "תשובותיך לסקר התקציב נשמרו בהצלחה.",
            "en": "Your responses to the budget survey have been successfully saved.",
        },
        "create_vector_title": {
            "he": "מהי חלוקת התקציב הטובה ביותר לדעתכם?",
            "en": "What is the best budget allocation in your opinion?",
        },
        "budget_instructions": {
            "he": 'חלקו תקציב של 100 מיליארד ש"ח בין שלושה משרדים: {subjects}.',
            "en": "Allocate a budget of 100 billion NIS between three ministries: {subjects}.",
        },
        "sum_note": {
            "he": {
                "title": "כללים",
                "rules": [
                    "בחרו ערכים בין 0-95 לכל משרד (אף משרד לא יכול לקבל את כל התקציב)",
                    "הסכום הכולל חייב להיות בדיוק 100",
                ],
            },
            "en": {
                "title": "Rules",
                "rules": [
                    "Choose values between 0-95 for each ministry (no single ministry can receive the entire budget)",
                    "Total must equal exactly 100",
                ],
            },
        },
        "total": {"he": 'סה"כ:', "en": "Total:"},
        "consent_title": {"he": "טופס הסכמה", "en": "Consent Form"},
        "consent_text": {
            "he": "לפני התחלת המענה על השאלון, נבקשך להצהיר/ה בזאת כי ניתן לך מידע באשר למחקר ולמטרותיו, וכי מילוי השאלון נעשה מרצונך החופשי, שהנך משתתפ/ת במחקר מתוך הסכמה מלאה, ידוע לך כי אינך חייב/ת להשתתף במחקר וכי בכל שלב את/ה יכול/ה להפסיק לענות על השאלון. השאלון הוא אנונימי ומובטחת לך סודיות באשר לזהותך האישית ולא יעשה כל שימוש בפרטים שמלאת מלבד לצורך מחקר זה. בכל בעיה שקשורה למחקר תוכל/י לפנות אלינו להתייעצות נוספת.",
            "en": "Before starting the questionnaire, please declare that you have been given information about the research and its objectives, that completing the questionnaire is done of your own free will, that you are participating in the research with full consent, you know that you are not obligated to participate in the research and that at any stage you can stop answering the questionnaire. The questionnaire is anonymous and you are guaranteed confidentiality regarding your personal identity and no use will be made of the details you filled in except for this research. For any problem related to the research, you can contact us for further consultation.",
        },
        "start_survey": {"he": "התחל סקר", "en": "Start Survey"},
        "consent_agreement": {
            "he": "אם את/ה מבין/ה ומסכים/ה להשתתף במחקר, אנא לחצ/י על הכפתור למטה.",
            "en": "If you understand and agree to participate in the research, please click the button below.",
        },
        "consent_disagreement": {
            "he": "אם אינך מבין/ה או לא רוצה להשתתף במחקר, אנא סגור/י את הדפדפן.",
            "en": "If you don't understand or don't want to participate in the research, please close your browser.",
        },
        "microblog": {"he": "בלוג-מיקרו:", "en": "Microblog:"},
        "home": {"he": "דף הבית", "en": "Home"},
        "what_next": {"he": "מה הלאה?", "en": "What's Next?"},
        "next_steps": {
            "he": [
                "תשובותיך יעובדו יחד עם תשובות משתתפים אחרים.",
                "התוצאות ישמשו לניתוח ומחקר בנושא העדפות תקציביות.",
                "אנו לא נשתמש במידע אישי שלך מעבר למטרות המחקר.",
            ],
            "en": [
                "Your answers will be processed together with other participants' responses.",
                "The results will be used for analysis and research on budget preferences.",
                "We will not use your personal information beyond research purposes.",
            ],
        },
        "appreciation": {
            "he": "אנו מעריכים את הזמן והמחשבה שהשקעת בתשובותיך.",
            "en": "We appreciate the time and thought you invested in your responses.",
        },
        "comments_placeholder": {
            "he": "רשום את הערותיך כאן (רשות)",
            "en": "Write your comments here (optional)",
        },
        "error_page_title": {"he": "שגיאה - סקר התקציב", "en": "Error - Budget Survey"},
        "error_page_heading": {
            "he": "אופס! משהו השתבש",
            "en": "Oops! Something went wrong",
        },
    },
}


def get_current_language() -> str:
    """
    Get the current language from URL parameter or session.
    Returns default 'he' if neither is set.
    """
    # First check URL parameter
    url_lang = request.args.get("lang")
    if url_lang in ["he", "en"]:
        session["language"] = url_lang  # Update session with URL parameter
        return url_lang

    # Then fall back to session
    return session.get("language", "he")


def get_translation(
    key: str, section: str = "survey", language: Optional[str] = None, **kwargs
) -> str:
    """
    Get translation for a specific key with optional parameter substitution.

    Args:
        key: The translation key
        section: The section in translations dictionary (default: "survey")
        language: Language code (if None, uses current language from session)
        **kwargs: Parameters to substitute in the translation string

    Returns:
        str: Translated text with substituted parameters
    """
    lang = language or get_current_language()
    try:
        logger.debug(
            f"Translation request - section: {section}, key: {key}, lang: {lang}"
        )
        logger.debug(f"Available sections: {TRANSLATIONS.keys()}")
        logger.debug(
            f"Available keys in {section}: {TRANSLATIONS.get(section, {}).keys()}"
        )

        text = TRANSLATIONS[section][key][lang]
        # If there are parameters, format the string with them
        if kwargs:
            text = text.format(**kwargs)
        return text
    except KeyError as e:
        logger.error(
            f"Translation not found - section: {section}, key: {key}, lang: {lang}, error: {str(e)}"
        )
        return f"[{section}.{key}]"


def set_language(lang: str) -> bool:
    """
    Set the current language in session.

    Args:
        lang (str): Language code ('he' or 'en')

    Returns:
        bool: True if language was set successfully, False if invalid language code

    Note:
        Defaults to 'he' if an invalid language code is provided
        Valid language codes are 'he' (Hebrew) and 'en' (English)
    """
    if lang in ["he", "en"]:
        session["language"] = lang
        return True
    else:
        session["language"] = "he"  # Default to Hebrew for invalid codes
        return False
