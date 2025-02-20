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
            "he": "נא לוודא שהסכום הכולל הוא 100 ושכל המספרים מתחלקים ב-5. השתמשו בכפתור 'שנה קנה מידה' להתאמה אוטומטית.",
            "en": "Please ensure the total sum is 100 and all numbers are divisible by 5. Use the 'Rescale' button for automatic adjustment.",
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
        "survey_not_found": {
            "he": "סקר מספר {survey_id} לא נמצא",
            "en": "Survey #{survey_id} not found",
        },
        "survey_no_subjects": {
            "he": "סקר מספר {survey_id} לא נמצא או אין לו נושאים",
            "en": "Survey #{survey_id} not found or has no subjects",
        },
        "report_error": {
            "he": "אירעה שגיאה בהפקת הדוח. אנא נסה שוב מאוחר יותר.",
            "en": "An error occurred generating the report. Please try again later.",
        },
        "dashboard_error": {
            "he": "שגיאה בטעינת לוח הבקרה",
            "en": "Error loading dashboard",
        },
        "dashboard_refreshed": {
            "he": "הנתונים עודכנו בהצלחה",
            "en": "Data refreshed successfully",
        },
        "dashboard_refresh_error": {
            "he": "שגיאה בעדכון הנתונים",
            "en": "Error refreshing dashboard data",
        },
        "survey_not_found_or_empty": {
            "he": "סקר {survey_id} לא נמצא או שאין לו תשובות. אנא בדקו את מספר הסקר ונסו שוב.",
            "en": "Survey {survey_id} was not found or has no answers. Please verify the survey ID and try again.",
        },
        "survey_retrieval_error": {
            "he": "אירעה שגיאה בעת אחזור נתוני הסקר. אנא נסו שוב מאוחר יותר.",
            "en": "An error occurred while retrieving the survey data. Please try again later.",
        },
        "invalid_parameter": {
            "en": "Invalid parameter provided",
            "he": "פרמטר לא חוקי",
        },
        "rescale_error_too_small": {
            "he": "לא ניתן לשנות קנה מידה כאשר הסכום הכולל הוא 0",
            "en": "Cannot rescale when the total sum is 0",
        },
        "rescale_error_too_many_zeros": {
            "he": "לא ניתן לשנות קנה מידה כאשר יותר ממשרד אחד מקבל 0. שנו לפחות אחד מהערכים להיות מעל 0.",
            "en": "Cannot rescale when more than one ministry has 0. Change at least one value to be above 0.",
        },
        "min_two_departments": {
            "he": "יש להקצות תקציב לשני משרדים לפחות.",
            "en": "Budget must be allocated to at least two departments.",
        },
        "missing_budget": {
            "he": "נא להזין את הקצאת התקציב",
            "en": "Missing budget allocation",
        },
        "budget_sum_error": {
            "he": "סכום התקציב חייב להיות 100",
            "en": "Budget allocation must sum to 100",
        },
        "budget_range_error": {
            "he": "ערכי התקציב חייבים להיות בין 0 ל-95",
            "en": "Budget values must be between 0 and 95",
        },
        "invalid_pairs_count": {
            "he": "מספר זוגות ההשוואה אינו תקין",
            "en": "Incorrect number of comparison pairs",
        },
        "invalid_pair_at_position": {
            "he": "זוג השוואה לא תקין במיקום {position}",
            "en": "Invalid comparison pair at position {position}",
        },
        "validation_error": {
            "he": "שגיאה בתהליך האימות",
            "en": "Internal validation error",
        },
        "invalid_pair_strategy": {
            "he": "אסטרטגיית יצירת הזוגות '{strategy}' אינה קיימת",
            "en": "Pair generation strategy '{strategy}' does not exist",
        },
        "pair_generation_error": {
            "he": "שגיאה ביצירת הזוגות ",
            "en": "Error generating comparison pairs",
        },
        "invalid_pair_config": {
            "he": "קונפיגרצית יצירת הזוגות אינה תקינה",
            "en": "Invalid pair generation configuration",
        },
        "strategy_execution_error": {
            "he": "שגיאה בביצוע אסטרטגיית יצירת הזוגות",
            "en": "Error executing pair generation strategy",
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
        "submit_next_stage": {
            "he": "התקדם לשלב הבא בסקר",
            "en": "Proceed to the Next Stage",
        },
        "submit_final": {"he": "שלח סקר", "en": "Submit Survey"},
        "thank_you": {
            "he": "תודה רבה על השתתפותך!",
            "en": "Thank you for your participation!",
        },
        "thank_you_message": {
            "he": "תשובותיך לסקר התקציב נשמרו בהצלחה.",
            "en": "Your responses to the budget survey have been successfully saved.",
        },
        "create_vector_title": {
            "he": "מהי חלוקת התקציב הטובה ביותר לדעתך?",
            "en": "What is the best budget allocation in your opinion?",
        },
        "budget_instructions": {
            "he": 'חלקו תקציב של 100 מיליארד ש"ח בין שלושה משרדים: {subjects}.',
            "en": "Allocate a budget of 100 billion NIS between three ministries: {subjects}.",
        },
        "sum_note": {
            "he": {
                "title": "שימו לב",
                "rules": [
                    "הזינו ערכים עבור כל משרד",
                    "ניתן להשתמש בכפתור 'שנה קנה מידה' כדי להתאים את הערכים באופן יחסי לסכום של 100",
                    "יש להקצות תקציב לשני משרדים לפחות",
                    "בסוף התהליך הסכום הכולל חייב להיות בדיוק 100",
                ],
            },
            "en": {
                "title": "Instructions",
                "rules": [
                    "Enter values for each ministry",
                    "Use the 'Rescale' button to proportionally adjust your values to sum to 100",
                    "The budget must be allocated to at least two departments",
                    "The final total must equal exactly 100",
                ],
            },
        },
        "rescale_button": {"he": "התאם את הסכום ל-100", "en": "Rescale to 100"},
        "rescale_tooltip": {
            "he": "התאמה אוטומטית של הערכים באופן יחסי כך שיסתכמו ל-100",
            "en": "Automatically adjust values proportionally to sum to 100",
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
    "dashboard": {  # Dashboard page
        "refresh": {"he": "רענן נתונים", "en": "Refresh Data"},
        "last_updated": {"he": "עודכן לאחרונה", "en": "Last Updated"},
        "completion_rate": {"he": "אחוז השלמה", "en": "Completion Rate"},
        "expand": {"he": "הרחב", "en": "Expand"},
        "download": {"he": "הורד", "en": "Download"},
        "survey_percentages": {
            "he": "התפלגות התשובות לפי סקר",
            "en": "Survey Answer Percentages",
        },
        "majority_choices": {"he": "בחירת רוב המשתמשים", "en": "User Majority Choices"},
        "overall_distribution": {"he": "התפלגות כללית", "en": "Overall Distribution"},
        "answer_distribution": {"he": "התפלגות התשובות", "en": "Answer Distribution"},
        "survey_analysis": {"he": "ניתוח הסקר", "en": "Survey Analysis"},
        "choice_distribution": {"he": "התפלגות הבחירות", "en": "Choice Distribution"},
        "user_choices": {"he": "בחירות המשתמשים", "en": "User Choices"},
        "user_id": {"he": "מזהה המשתמש", "en": "User ID"},
        "survey": {"he": "סקר", "en": "Survey"},
        "strategy": {"he": "אסטרטגיה", "en": "Strategy"},
        "title": {"he": "פאנל הסקרים", "en": "Surveys Overview"},
        "subtitle": {
            "he": "צפה ונהל את הסקרים הפעילים",
            "en": "View and manage active surveys",
        },
        "total_surveys": {"he": "סך כל הסקרים", "en": "Total Surveys"},
        "total_participants": {"he": "סך כל המשתתפים", "en": "Total Participants"},
        "view_details": {"he": "צפה בפרטים", "en": "View Details"},
        "view_responses": {"he": "צפה בתשובות", "en": "View Responses"},
        "take_survey": {"he": "מלא סקר", "en": "Take Survey"},
    },
    "answers": {  # Answers page
        "title": {"he": "תשובות לכל הסקרים", "en": "Survey Answers"},
        "survey_title": {
            "he": "תשובות לסקר מספר {survey_id}",
            "en": "Survey #{survey_id} Answers",
        },
        "no_answers": {"he": "אין תשובות זמינות.", "en": "No answers available."},
        "comments_title": {"he": "הערות המשתמשים", "en": "User Comments"},
        "no_comments": {"he": "אין הערות זמינות.", "en": "No comments available."},
        "survey_answers_tab": {"he": "תשובות הסקר", "en": "Survey Answers"},
        "survey_comments_tab": {"he": "הערות המשתתפים", "en": "Participant Comments"},
        "view_all_comments": {"he": "צפה בכל ההערות", "en": "View All Comments"},
        "original_choice": {"he": "בחירה מקורית", "en": "Original choice"},
        "not_available": {"he": "לא זמין", "en": "Not available"},
        "pair_number": {"he": "זוג מספר", "en": "Pair"},
        "table_choice": {"he": "בחירה", "en": "Choice"},
        "table_option": {"he": "אפשרות", "en": "Option"},
        "table_type": {"he": "סוג", "en": "Type"},
        "option_number": {"he": "אפשרות {number}", "en": "Option {number}"},
        "user_responses_title": {
            "he": "תשובות משתמש {user_id} לסקר {survey_id}",
            "en": "User {user_id} Responses to survey {survey_id}",
        },
        "user_responses_title_short": {
            "he": "תשובות משתמש {user_id}",
            "en": "User {user_id} Responses",
        },
        "no_user_responses": {
            "he": "לא נמצאו תשובות למשתמש {user_id}",
            "en": "No responses found for user {user_id}",
        },
        "back_to_list": {"he": "חזרה לרשימת התשובות", "en": "Back to Responses List"},
        # Main titles and sections
        "overall_statistics": {
            "he": "סטטיסטיקות כלליות",
            "en": "Overall Survey Statistics",
        },
        "survey_response_breakdown": {
            "he": "פילוח תשובות הסקר",
            "en": "Survey Response Breakdown",
        },
        "survey_summary": {"he": "סיכום הסקר", "en": "Survey Summary"},
        # Table headers and labels
        "average_percentage": {"he": "אחוז ממוצע", "en": "Average Percentage"},
        "metric": {"he": "מדד", "en": "Metric"},
        "percentage": {"he": "אחוז", "en": "Percentage"},
        "choice": {"he": "בחירה", "en": "Choice"},
        # Identifiers and metadata
        "survey_id": {"he": "מזהה סקר", "en": "Survey ID"},
        "user_id": {"he": "מזהה משתמש", "en": "User ID"},
        "ideal_budget": {"he": "תקציב אידיאלי", "en": "Ideal budget"},
        # Response count template
        "based_on_responses": {
            "he": "מבוסס על {x} תשובות לסקר",
            "en": "Based on {x} survey responses",
        },
        "view_response": {"he": "צפה בתשובה", "en": "View Response"},
    },
}


def get_current_language(default_lang="he") -> str:
    """
    Get the current language from URL parameter or session.
    Returns default 'he' if neither is set.
    """
    try:
        # First check URL parameter
        url_lang = request.args.get("lang")
        if url_lang in ["he", "en"]:
            session["language"] = url_lang  # Update session with URL parameter
            return url_lang

        # Then fall back to session
        return session.get("language", default_lang)
    except RuntimeError:
        # Outside request context, return default
        return default_lang


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
