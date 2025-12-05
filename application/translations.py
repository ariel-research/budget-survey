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
            "he": "נא לוודא שהסכום הכולל הוא 100 ושכל המספרים מתחלקים ב-5. "
            "השתמשו בכפתור 'שנה קנה מידה' להתאמה אוטומטית.",
            "en": "Please ensure the total sum is 100 and all numbers are "
            "divisible by 5. Use the 'Rescale' button for automatic adjustment.",
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
            "he": "לא ניתן לשנות קנה מידה כאשר יותר מנושא אחד מקבל 0. "
            "שנו לפחות אחד מהערכים להיות מעל 0.",
            "en": "Cannot rescale when more than one issue has 0. "
            "Change at least one value to be above 0.",
        },
        "min_two_departments": {
            "he": "יש להקצות תקציב לשני נושאים שונים לפחות.",
            "en": "Budget must be allocated to at least two issues.",
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
        "demo_mode": {
            "he": "מצב הדגמה - הנתונים אינם נשמרים",
            "en": "DEMO MODE - Data not saved",
        },
        "attention_check_title": {
            "he": "בדיקת הערנות נכשלה",
            "en": "Attention check failed",
        },
        "attention_check_failed": {
            "he": "לא עברת את בדיקת תשומת הלב",
            "en": "Failed attention check",
        },
        "early_awareness_failed": {
            "he": "לא עברת את בדיקת הערנות. התשובות שלך נשמרו. אתה מועבר חזרה Panel4All.",
            "en": "You did not pass the attention check. Your responses have been recorded and you are being redirected back to Panel4All.",
        },
        "redirecting_in_seconds": {
            "he": "מועבר בעוד {seconds} שניות...",
            "en": "Redirecting in {seconds} seconds...",
        },
        "user_blacklisted": {
            "he": "המשתמש חסום מהשתתפות בסקרים עקב כישלון בבדיקת הערנות",
            "en": "User is blacklisted from participating in surveys due to failing attention checks",
        },
        "no_data_available": {
            "he": "אין נתונים זמינים להצגה",
            "en": "No data available to display",
        },
        "matrix_generation_error": {
            "he": "שגיאה ביצירת מטריצת המשתמשים",
            "en": "Error generating the user matrix",
        },
        "no_responses_to_download": {
            "he": "אין תשובות זמינות להורדה עבור סקר {survey_id}",
            "en": "No responses available for download for survey {survey_id}",
        },
    },
    "pagination": {  # Pagination controls
        "previous": {
            "he": "הקודם",
            "en": "Previous",
        },
        "next": {
            "he": "הבא",
            "en": "Next",
        },
        "page_info": {
            "he": "עמוד {page} מתוך {total_pages}",
            "en": "Page {page} of {total_pages}",
        },
        "page_info_with_users": {
            "he": "עמוד {page} מתוך {total_pages} ({total_users} סך המשתמשים)",
            "en": "Page {page} of {total_pages} ({total_users} users total)",
        },
        "users_total": {
            "he": "{total_users} סך המשתמשים",
            "en": "{total_users} users total",
        },
        "showing_page_data": {
            "he": "מציג נתונים עבור עמוד {page} בלבד",
            "en": "Showing data for page {page} only",
        },
        "current_page_summary": {
            "he": "הסיכום מתייחס לעמוד הנוכחי בלבד ({users_count} משתמשים)",
            "en": "Summary refers to current page only ({users_count} users)",
        },
        "first": {
            "he": "ראשון",
            "en": "First",
        },
        "last": {
            "he": "אחרון",
            "en": "Last",
        },
        "go_to_page": {
            "he": "עבור לעמוד {page}",
            "en": "Go to page {page}",
        },
        "current_page": {
            "he": "עמוד נוכחי {page}",
            "en": "Current page {page}",
        },
        "loading": {
            "he": "טוען...",
            "en": "Loading...",
        },
    },
    "survey": {  # Survey content
        "welcome": {"he": "ברוכים הבאים לסקר", "en": "Welcome to the Survey"},
        "intro_text": {
            "he": "נעים מאוד, אנו פרופ' אראל סגל-הלוי מאוניברסיטת אריאל ופרופ' ריקה גונן מהאוניברסיטה הפתוחה עורכים מחקר בנושא העדפות אזרחים לגבי חלוקת תקציב. אנו מזמינים אותך להשתתף במחקר שלנו על ידי מתן מענה על שאלון מקוון שאורכו כ-5 דקות.",
            "en": "Hello, we are Prof. Erel Segal-Halevi from Ariel University and Prof. Rica Gonen from the Open University. We are conducting research on citizens' preferences regarding budget allocation. We invite you to participate in our research by answering an online questionnaire that takes about 5 minutes.",
        },
        "survey_responses_title": {"he": "תוצאות הסקר", "en": "Survey Responses"},
        "survey_responses_for": {
            "he": "תוצאות עבור הסקר",
            "en": "Responses for Survey",
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
            "he": "אבל במציאות, חלוקת התקציב לא זהה לחלוקה האידיאלית שלך. בהמשך נציג לפניך זוגות של חלוקות-תקציב לא אידיאליות. עבור כל אחד מהזוגות, עליך לבחור איזו מבין שתי החלוקות טובה יותר בעיניך.",
            "en": "However, in reality, the budget allocation differs from your ideal allocation. We will present you with pairs of non-ideal budget allocations. For each pair, you need to choose which of the two allocations is better in your opinion.",
        },
        "pair": {"he": "זוג", "en": "Pair"},
        "option": {"he": "אפשרות", "en": "Option"},
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
            "he": 'חלקו תקציב של 100 מיליארד ש"ח בין שלושה נושאים: {subjects}.',
            "en": "Allocate a budget of 100 billion NIS between three issues: {subjects}.",
        },
        "sum_note": {
            "he": {
                "title": "שימו לב",
                "rules": [
                    "הזינו ערכים עבור כל נושא",
                    "כל הערכים חייבים להתחלק ב-5 (כפולות של 5)",
                    "ניתן להשתמש בכפתור 'התאם את הסכום' כדי להתאים את הערכים באופן יחסי לסכום של 100",
                    "יש להקצות תקציב לשני נושאים שונים לפחות",
                    "בסוף התהליך הסכום הכולל חייב להיות בדיוק 100",
                ],
            },
            "en": {
                "title": "Instructions",
                "rules": [
                    "Enter monetary value for each issue",
                    "All values must be divisible by 5 (multiples of 5)",
                    "Use the 'Rescale' button to proportionally adjust your values to sum to 100",
                    "The budget must be allocated to at least two different issues",
                    "The final total must equal exactly 100",
                ],
            },
        },
        "rescale_button": {"he": "התאם את הסכום ל-100", "en": "Rescale to 100"},
        "rescale_tooltip": {
            "he": "התאמה אוטומטית של הערכים באופן יחסי כך שיסתכמו ל-100",
            "en": "Automatically adjust values proportionally to sum to 100",
        },
        "total": {"he": "סך הכל", "en": "Total"},
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
        "blacklisted_title": {
            "he": "חסימת משתמש",
            "en": "User Blacklisted",
        },
        "blacklisted_message": {
            "he": "חשבונך נחסם מהשתתפות בסקרים עתידיים עקב כישלון בבדיקות הערנות. משתמשים שאינם עוקבים אחר ההנחיות בצורה זהירה נחסמים באופן אוטומטי.",
            "en": "Your account has been blacklisted from participating in future surveys due to failing attention checks. Users who do not carefully follow instructions are automatically blacklisted.",
        },
        "close_window": {
            "he": "סגור חלון",
            "en": "Close Window",
        },
        "unsuitable_title": {
            "he": "לא מתאים לסקר",
            "en": "Unsuitable for Survey",
        },
        "unsuitable_message": {
            "he": "אינך מתאים לסקר זה.",
            "en": "You are not suitable for this survey.",
        },
        # Ranking survey interface
        "question": {"he": "שאלה", "en": "Question"},
        "ranking_instructions": {
            "he": "אנא דרגו את שלושת האפשרויות הבאות מהטובה ביותר לגרועה ביותר "
            "(1 = הטובה ביותר, 3 = הגרועה ביותר)",
            "en": "Please rank the following three options from best to worst "
            "(1 = best, 3 = worst)",
        },
        "option_a_label": {"he": "אפשרות א׳", "en": "Option A"},
        "option_b_label": {"he": "אפשרות ב׳", "en": "Option B"},
        "option_c_label": {"he": "אפשרות ג", "en": "Option C"},
        "rank_1": {"he": "דירוג 1", "en": "Rank 1"},
        "rank_2": {"he": "דירוג 2", "en": "Rank 2"},
        "rank_3": {"he": "דירוג 3", "en": "Rank 3"},
        "most_preferred": {"he": "הטוב ביותר", "en": "Most preferred"},
        "least_preferred": {"he": "הגרוע ביותר", "en": "Least preferred"},
        "select_option": {"he": "בחרו אפשרות", "en": "Select option"},
        "ranking_validation_error": {
            "he": "אנא דרגו את כל האפשרויות עבור כל שאלה",
            "en": "Please rank all options for each question",
        },
        "duplicate_ranking_error": {
            "he": "לא ניתן לתת את אותו דירוג לשתי אפשרויות",
            "en": "Cannot give the same rank to multiple options",
        },
        "rank_this_option": {
            "he": "דרגו אפשרות זו",
            "en": "Rank this option",
        },
        "select_rank": {
            "he": "בחרו דירוג",
            "en": "Select rank",
        },
        # Temporal preference analysis
        "temporal_awareness_instruction": {
            "he": "זוהי <strong>בדיקת ערנות</strong>. אנא בחר את <em>התקציב האידיאלי</em> שלך.",
            "en": "This is an <strong>awareness check</strong>. Please select your <em>ideal budget</em>.",
        },
        "temporal_simple_discounting_instruction": {
            "he": (
                "עליכם לקבוע את התקציב עבור <strong>שתי שנים עוקבות</strong>: "
                "השנה הנוכחית, והשנה הבאה. איזה מבין שני התקציבים הבאים תעדיפו "
                "שיהיה התקציב <strong>בשנה הנוכחית</strong>? התקציב שלא תבחרו יהיה "
                "התקציב <strong>בשנה הבאה</strong>."
            ),
            "en": (
                "You need to set the budget for <strong>two consecutive "
                "years</strong>: <strong>the current year</strong> and "
                "<strong>next year</strong>. Which of the following two "
                "budgets would you prefer to be <strong>the current year's "
                "budget</strong>? The budget you don't choose will be "
                "<strong>next year's budget</strong>."
            ),
        },
        "temporal_second_year_choice_instruction": {
            "he": (
                "התקציב לשנה <strong>הנוכחית</strong> קבוע: <strong>{vector_b_formatted}</strong>. "
                "אנא בחרו את התקציב המועדף עליכם לשנה <strong>הבאה</strong>."
            ),
            "en": (
                "The budget for the <strong>current</strong> year is fixed at: "
                "<strong>{vector_b_formatted}</strong>. Please choose your "
                "preferred budget for the <strong>next</strong> year."
            ),
        },
        "temporal_first_year_choice_instruction": {
            "he": (
                "התקציב לשנה <strong>הבאה</strong> קבוע: <strong>{vector_b_formatted}</strong>. "
                "אנא בחרו את התקציב המועדף עליכם לשנה <strong>הנוכחית</strong>."
            ),
            "en": (
                "The budget for the <strong>next</strong> year is fixed at: "
                "<strong>{vector_b_formatted}</strong>. Please choose your "
                "preferred budget for the <strong>current</strong> year."
            ),
        },
        # Triangle inequality screening
        "screening_title": {"he": "שאלות מיון", "en": "Screening Questions"},
        "screening_instruction": {
            "he": "לפני שנתחיל, יש לנו שתי שאלות קצרות כדי להבין את העדפותיך.",
            "en": "Before we begin, we have two short questions to understand your preferences.",
        },
        "screening_q1_prompt": {
            "he": "התקציב לשנה 1 קבוע. אנא בחרו את התקציב המועדף עליכם לשנה 2.",
            "en": "The budget for Year 1 is fixed. Please choose your preferred budget for Year 2.",
        },
        "screening_q2_prompt": {
            "he": "התקציב לשנה 2 קבוע. אנא בחרו את התקציב המועדף עליכם לשנה 1.",
            "en": "The budget for Year 2 is fixed. Please choose your preferred budget for Year 1.",
        },
        "year_1_fixed": {"he": "תקציב שנה 1 (קבוע)", "en": "Year 1 Budget (Fixed)"},
        "year_2_fixed": {"he": "תקציב שנה 2 (קבוע)", "en": "Year 2 Budget (Fixed)"},
        "your_choice_for_year": {
            "he": "הבחירה שלך לשנה {year}",
            "en": "Your choice for Year {year}",
        },
        "screening_failed": {
            "he": "תודה על השתתפותך. תשובותיך מצביעות על העדפות שאינן מתאימות לסוג הסקר הזה.",
            "en": "Thank you for your participation. Your answers indicate preferences that are not suitable for this type of survey.",
        },
        "proceed_to_main_survey": {
            "he": "המשך לשלב הבא בסקר",
            "en": "Proceed to Main Survey",
        },
        # Triangle inequality test
        "triangle_inequality_instruction": {
            "he": "עליכם לבחור בין שתי אפשרויות תקציב דו-שנתיות. כל אפשרות מציגה את התקציב לשנה הנוכחית ולשנה הבאה.",
            "en": "You need to choose between two biennial budget options. Each plan shows the budget for the current year and next year.",
        },
        "year_1_budget": {"he": "שנה 1", "en": "Year 1"},
        "year_2_budget": {"he": "שנה 2", "en": "Year 2"},
        "year_1": {"he": "שנה 1", "en": "Year 1"},
        "year_2": {"he": "שנה 2", "en": "Year 2"},
        "group_rotation_explanation_line1": {
            "he": "קבוצה (G1/G2) = שני תרחישי שינוי תקציב שונים",
            "en": "Group (G1/G2) = Two different budget change scenarios",
        },
        "group_rotation_explanation_line2": {
            "he": "סיבוב (R0/R1/R2) = סיבוב מעגלי של הקטגוריות המושפעות",
            "en": "Rotation (R0/R1/R2) = Cyclic rotation of affected categories",
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
        "blacklisted_users_title": {
            "he": "משתמשים חסומים",
            "en": "Blacklisted Users",
        },
        "unaware_users": {
            "he": "משתמשים לא ערניים",
            "en": "Unaware Users",
        },
        "blacklisted_users_subtitle": {
            "he": "רשימת המשתמשים שנחסמו בשל כישלון בבדיקות הערנות",
            "en": "Users who have been blacklisted for failing attention checks",
        },
        "blacklisted_at": {
            "he": "תאריך החסימה",
            "en": "Blacklisted At",
        },
        "failed_survey_title": {
            "he": "כותרת הסקר",
            "en": "Survey Title",
        },
        "no_blacklisted_users": {
            "he": "אין משתמשים חסומים במערכת",
            "en": "No blacklisted users in the system",
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
        "total_surveys_description": {
            "he": "סקרים פעילים במערכת",
            "en": "Active surveys in the system",
        },
        "total_participants": {
            "he": "עברו בדיקות איכות (בדיקות ערנות)",
            "en": "Passed Quality Checks (Attention Checks)",
        },
        "excluded_users": {"he": "משתמשים חסומים", "en": "Blocked Users"},
        "all_participants": {"he": "כל המשתתפים", "en": "All Survey Completers"},
        "all_participants_description": {
            "he": "משתמשים שהשלימו סקרים (כולל כאלה שנכשלו בבדיקות איכות/ערנות)",
            "en": "Users who completed surveys (including those who failed quality/attention checks)",
        },
        "total_participants_description": {
            "he": "משתמשים שהשלימו סקרים ועברו בדיקות איכות (ערנות)",
            "en": "Users who completed surveys and passed quality (attention) checks",
        },
        "excluded_users_description": {
            "he": "משתמשים החסומים כעת",
            "en": "Currently blocked users",
        },
        "view_details": {"he": "צפה בפרטים", "en": "View Details"},
        "view_responses": {"he": "צפה בתשובות", "en": "View Responses"},
        "take_survey": {"he": "מלא סקר", "en": "Take Survey"},
    },
    "answers": {  # Answers page
        "title": {"he": "תשובות לכל הסקרים", "en": "Survey Answers"},
        "survey_title": {
            "he": "תוצאות סקר #{survey_id}",
            "en": "Survey #{survey_id} Results",
        },
        "no_answers": {
            "he": "לא נמצאו תשובות לסקר זה",
            "en": "No answers found for this survey",
        },
        "no_user_responses": {
            "he": "לא נמצאו תשובות עבור משתמש {user_id}",
            "en": "No responses found for user {user_id}",
        },
        "user_survey_responses": {
            "he": "תשובות המשתמש {user_id} לסקר #{survey_id}",
            "en": "User {user_id} Responses for Survey #{survey_id}",
        },
        "user_responses": {
            "he": "תשובות המשתמש {user_id}",
            "en": "User {user_id} Responses",
        },
        "back_to_responses": {
            "he": "חזרה לכל התשובות",
            "en": "Back to all responses",
        },
        "survey_answers_tab": {
            "he": "תשובות",
            "en": "Answers",
        },
        "survey_comments_tab": {
            "he": "הערות",
            "en": "Comments",
        },
        "user_filter": {
            "he": "סנן משתמשים:",
            "en": "Filter Users:",
        },
        "all_users": {
            "he": "כל המשתמשים",
            "en": "All Users",
        },
        "weighted_vector_users": {
            "he": "משתמשים המעדיפים וקטורים משוקללים",
            "en": "Users Preferring Weighted Vectors",
        },
        "rounded_weighted_vector_users": {
            "he": "משתמשים המעדיפים וקטורים משוקללים מעוגלים",
            "en": "Users Preferring Rounded Weighted Vectors",
        },
        "any_weighted_vector_users": {
            "he": "משתמשים המעדיפים וקטורים משוקללים כלשהם",
            "en": "Users Preferring Any Weighted Vectors",
        },
        "filtered_view": {
            "he": "תצוגה מסוננת",
            "en": "Filtered View",
        },
        "clear_filter": {
            "he": "נקה סינון",
            "en": "Clear",
        },
        "download_csv": {
            "he": "הורד CSV",
            "en": "Download CSV",
        },
        "download_csv_tooltip": {
            "he": "הורד את נתוני התשובות בפורמט CSV",
            "en": "Download response data in CSV format",
        },
        "comments_title": {"he": "הערות המשתמשים", "en": "User Comments"},
        "view_all_comments": {"he": "צפה בכל ההערות", "en": "View All Comments"},
        "no_comments": {"he": "אין הערות זמינות.", "en": "No comments available."},
        "original_choice": {"he": "בחירה מקורית", "en": "Original choice"},
        "not_available": {"he": "לא זמין", "en": "Not available"},
        "pair_number": {"he": "זוג מספר", "en": "Pair"},
        "table_choice": {"he": "בחירה", "en": "Choice"},
        "table_option": {"he": "אפשרות", "en": "Option"},
        "table_type": {"he": "סוג", "en": "Type"},
        "option_number": {"he": "אפשרות {number}", "en": "Option {number}"},
        "option_a_label": {"he": "אפשרות א", "en": "Option A"},
        "option_b_label": {"he": "אפשרות ב", "en": "Option B"},
        "user_responses_title": {
            "he": "תשובות משתמש {user_id} לסקר {survey_id}",
            "en": "User {user_id} Responses to survey {survey_id}",
        },
        "user_responses_title_short": {
            "he": "תשובות משתמש {user_id}",
            "en": "User {user_id} Responses",
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
        "far_vector": {
            "he": "וקטור רחוק",
            "en": "Far Vector",
        },
        "near_vector": {
            "he": "וקטור קרוב",
            "en": "Near Vector",
        },
        # Table headers and labels
        "average_percentage": {
            "he": "אחוז ממוצע",
            "en": "Average Percentage",
        },
        "metric": {"he": "מדד", "en": "Metric"},
        "percentage": {"he": "אחוז", "en": "Percentage"},
        "choice": {"he": "בחירה", "en": "Choice"},
        "response_time": {"he": "זמן תגובה", "en": "Response Time"},
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
        # Extreme vector analysis
        "extreme_analysis_title": {
            "he": "סיכום העדפות וקטורי קיצון (משתמש יחיד)",
            "en": "Extreme Vector Preferences Summary (Single User)",
        },
        "extreme_analysis_note": {
            "he": "הערה: הטבלה מסכמת את בחירות המשתמש ({processed_pairs} זוגות).",
            "en": "Note: Table summarizes user choices ({processed_pairs} pairs).",
        },
        "th_empty": {"he": "", "en": ""},
        "prefer_a": {"he": "מעדיפים א", "en": "Prefer A"},
        "prefer_b": {"he": "מעדיפים ב", "en": "Prefer B"},
        "prefer_c": {"he": "מעדיפים ג", "en": "Prefer C"},
        "a_vs_b": {"he": "א לעומת ב", "en": "A vs B"},
        "a_vs_c": {"he": "א לעומת ג", "en": "A vs C"},
        "b_vs_c": {"he": "ב לעומת ג", "en": "B vs C"},
        "consistent": {"he": "עקבי", "en": "Consistent"},
        "inconsistent": {"he": "לא עקבי", "en": "Inconsistent"},
        "consistency": {"he": "עקביות", "en": "consistency"},
        "overall_consistency": {"he": "עקביות כוללת", "en": "Overall Consistency"},
        "transitivity_rate": {
            "he": "שיעור הטרנזיטיביות",
            "en": "Transitivity Rate",
        },
        "order_consistency": {"he": "עקביות סדר העדפות", "en": "Order Consistency"},
        "user_optimizes": {"he": "אופטימיזצית משתמש", "en": "User optimizes"},
        "sum_of_differences": {"he": "סכום ההפרשים", "en": "Sum of differences"},
        "minimum_ratio": {"he": "יחס מינימלי", "en": "Minimum ratio"},
        "sum_optimized": {"he": "אופטימיזציה לפי סכום", "en": "Sum optimized"},
        "ratio_optimized": {"he": "אופטימיזציה לפי יחס", "en": "Ratio optimized"},
        "sum": {"he": "סכום", "en": "Sum"},
        "ratio": {"he": "יחס", "en": "Ratio"},
        "root_sum_squared": {"he": "שורש סכום הריבועים", "en": "Root Sum Squared"},
        "weighted_average": {"he": "ממוצע משוקלל", "en": "Weighted Average"},
        "random": {"he": "אקראי", "en": "Random"},
        "none": {"he": "אין", "en": "none"},
        "extreme_1": {"he": "קיצוני 1", "en": "Extreme 1"},
        "extreme_2": {"he": "קיצוני 2", "en": "Extreme 2"},
        "cyclic_pattern_a": {"he": "דפוס מחזורי א", "en": "Cyclic Pattern A"},
        "cyclic_pattern_b": {"he": "דפוס מחזורי ב", "en": "Cyclic Pattern B"},
        "linear_positive": {"he": "דפוס ליניארי חיובי", "en": "Linear Positive"},
        "linear_negative": {"he": "דפוס ליניארי שלילי", "en": "Linear Negative"},
        "linear_consistency": {"he": "עקביות ליניארית", "en": "Linear Consistency"},
        "differences": {"he": "הבדלים", "en": "Differences"},
        "changes": {"he": "שינויים", "en": "Changes"},
        "no_matching_users": {
            "he": "אין משתמשים התואמים את קריטריון הסינון שנבחר.",
            "en": "No users match the selected filter criteria.",
        },
        "user_optimization_title": {
            "he": "אופטימיזציה של המשתמש",
            "en": "User Optimization",
        },
        "survey_response_title": {
            "he": "תשובות לסקר מספר {survey_id}",
            "en": "Responses for Survey #{survey_id}",
        },
        "extreme_vector_analysis_title": {
            "en": "Extreme Vector Analysis",
            "he": "ניתוח אקסטרים ווקטור",
        },
        "percentile_breakdown_title": {
            "en": "Percentile Consistency Breakdown",
            "he": ("פירוט עקביות " "לפי אחוזונים"),
        },
        "percentile": {"en": "Percentile", "he": "אחוזון"},
        "all_percentiles": {"en": "All Percentiles", "he": "כל האחוזונים"},
        "average_consistency": {"en": "Average Consistency", "he": "עקביות ממוצעת"},
        # Group consistency translations for cyclic shift
        "group_consistency": {
            "he": "עקביות",
            "en": "Consistency",
        },
        "group": {
            "he": "קבוצה",
            "en": "Group",
        },
        "consistency_percent": {
            "he": "אחוז עקביות",
            "en": "Consistency %",
        },
        "overall": {
            "he": "כללי",
            "en": "Overall",
        },
        "pairs_list": {
            "he": "רשימת זוגות",
            "en": "Pairs List",
        },
        "consistency_explanation": {
            "he": "אחוזים גבוהים יותר מעידים על בחירות עקביות יותר בקרב כל קבוצה",
            "en": "Higher percentages indicate more consistent choices within each group",
        },
        "groups": {
            "he": "קבוצות",
            "en": "groups",
        },
        "user_participation_title": {
            "he": "סקירת משתמשים",
            "en": "User Participation Overview",
        },
        "participation_overview_description": {
            "he": "סקירה כללית של המשתתפים בסקרים, המציגה "
            "סקרים שהסתיימו בהצלחה וכאלה שנכשלו.",
            "en": "An overview of user participation, showing successful and "
            "failed survey completions.",
        },
        "users_overview_description": {
            "he": "מציג {current_users_count} מתוך {total_users_count} משתמשים בסך הכל",
            "en": "Showing {current_users_count} of {total_users_count} total users",
        },
        "successful_surveys": {"he": "סקרים מוצלחים", "en": "Successful Surveys"},
        "failed_surveys": {"he": "סקרים שנכשלו", "en": "Failed Surveys"},
        "surveys": {"he": "סקרים", "en": "surveys"},
        "last_activity": {"he": "פעילות אחרונה", "en": "Last Activity"},
        "no_participation_data": {
            "he": "אין נתוני השתתפות",
            "en": "No participation data",
        },
        "user_survey_matrix": {
            "he": "מטריצת ביצועי משתמשים",
            "en": "User-Survey Performance Matrix",
        },
        "users_overview_tab": {
            "he": "סקירת משתמשים",
            "en": "Users Overview",
        },
        "user_matrix_tab": {
            "he": "מטריצת ביצועים",
            "en": "Performance Matrix",
        },
        "matrix_description": {
            "he": "מטריצה המציגה מדדי ביצוע ספציפיים עבור כל מענה לסקר. '-' מציין אי השתתפות.",
            "en": "Matrix showing strategy-specific performance metrics for each user-survey combination. '-' indicates no participation.",
        },
        "matrix_summary_users": {
            "he": "משתמשים",
            "en": "Users",
        },
        "matrix_summary_surveys": {
            "he": "סקרים",
            "en": "Surveys",
        },
        "matrix_summary_total_responses": {
            "he": "סך כל התשובות",
            "en": "Total Responses",
        },
        "survey_label": {
            "he": "סקר",
            "en": "Survey",
        },
        "concentrated_changes": {
            "he": "מרוכז (הפחתת יעד)",
            "en": "Concentrated (Target Decreases)",
        },
        "distributed_changes": {
            "he": "מבוזר (הגדלת יעד)",
            "en": "Distributed (Target Increases)",
        },
        # Temporal preference analysis
        "temporal_preference_summary": {
            "he": "סיכום העדפות זמניות",
            "en": "Temporal Preference Summary",
        },
        "ideal_this_year": {
            "he": "אידיאלי השנה",
            "en": "Ideal This Year",
        },
        "ideal_next_year": {
            "he": "אידיאלי בשנה הבאה",
            "en": "Ideal Next Year",
        },
        # Dynamic temporal preference sub-surveys
        "sub_survey_1_title": {
            "he": "תת-סקר 1: הנחה זמנית פשוטה",
            "en": "Sub-Survey 1: Simple Discounting",
        },
        "sub_survey_2_title": {
            "he": "תת-סקר 2: בחירת שנה ב'",
            "en": "Sub-Survey 2: Second-Year Choice",
        },
        "sub_survey_3_title": {
            "he": "תת-סקר 3: בחירת שנה א'",
            "en": "Sub-Survey 3: First-Year Choice",
        },
        "ideal_year_1": {
            "he": "אידיאלי שנה א'",
            "en": "Ideal Year 1",
        },
        "ideal_year_2": {
            "he": "אידיאלי שנה ב'",
            "en": "Ideal Year 2",
        },
        "balanced_year_1": {
            "he": "מאוזן שנה א'",
            "en": "Balanced Year 1",
        },
        "balanced_year_2": {
            "he": "מאוזן שנה ב'",
            "en": "Balanced Year 2",
        },
        "consistency_breakdown_title": {
            "he": "פילוח רמות עקביות",
            "en": "Consistency Breakdown",
        },
        "consistency_level": {
            "he": "רמת עקביות",
            "en": "Consistency Level",
        },
        "num_of_users": {
            "he": "מספר משתמשים",
            "en": "# of Users",
        },
        "avg_ideal_this_year": {
            "he": "ממוצע 'אידיאל השנה'",
            "en": "Avg. 'Ideal This Year' Choice",
        },
        "avg_ideal_next_year": {
            "he": "ממוצע 'אידיאל בשנה הבאה'",
            "en": "Avg. 'Ideal Next Year' Choice",
        },
        "avg_consistency": {
            "he": "ממוצע עקביות",
            "en": "Average Consistency",
        },
        "preference_consistency": {
            "he": "עקביות העדפות",
            "en": "Preference Consistency",
        },
        "magnitude_sensitivity": {
            "he": "רגישות לגודל השינוי",
            "en": "Magnitude Sensitivity",
        },
        "transitivity_analysis_title": {
            "he": "ניתוח טרנזיטיביות",
            "en": "Transitivity Analysis",
        },
        "preference_order": {
            "he": "סדר העדפה",
            "en": "Preference Order",
        },
        "transitivity_status": {
            "he": "סטטוס טרנזיטיביות",
            "en": "Transitivity Status",
        },
        "transitive": {
            "he": "טרנזיטיבי",
            "en": "Transitive",
        },
        "intransitive": {
            "he": "לא טרנזיטיבי",
            "en": "Intransitive",
        },
        "overall_transitivity_rate": {
            "he": "שיעור טרנזיטיביות כללי",
            "en": "Overall Transitivity Rate",
        },
        "order_stability": {
            "he": "עקביות סדר העדפות (קבוצות טרנזיטיביות)",
            "en": "Order Consistency (Transitive Groups)",
        },
        "total": {"he": 'סה"כ', "en": "Total"},
        "perfect_logical_consistency": {
            "he": "עקביות לוגית מושלמת",
            "en": "Perfect logical consistency",
        },
        "high_logical_consistency": {
            "he": "עקביות לוגית גבוהה",
            "en": "High logical consistency",
        },
        "moderate_consistency": {
            "he": "עקביות בינונית",
            "en": "Moderate consistency",
        },
        "low_consistency": {
            "he": "עקביות נמוכה",
            "en": "Low consistency",
        },
        "stable_preference_order": {
            "he": "סדר העדפות יציב בקבוצות הטרנזיטיביות",
            "en": "Stable preference order in transitive groups",
        },
        "partially_stable_order": {
            "he": "סדר יציב חלקית בקבוצות הטרנזיטיביות",
            "en": "Partially stable order in transitive groups",
        },
        "variable_preferences": {
            "he": "העדפות משתנות בקבוצות הטרנזיטיביות",
            "en": "Variable preferences in transitive groups",
        },
        "highly_variable_preferences": {
            "he": "העדפות משתנות מאוד בקבוצות הטרנזיטיביות",
            "en": "Highly variable preferences in transitive groups",
        },
        "decrease_target_by": {
            "he": "הפחתה המטרה ב-{amount}",
            "en": "Decrease target by {amount}",
        },
        "increase_target_by": {
            "he": "הגדלה המטרה ב-{amount}",
            "en": "Increase target by {amount}",
        },
        "target_is": {
            "he": "מטרה: {target_name}",
            "en": "Target: {target_name}",
        },
        "asymmetric_matrix_title": {
            "he": "מטריצת התפלגות הפסד אסימטרי",
            "en": "Asymmetric Loss Distribution Matrix",
        },
        "magnitude_levels_note": {
            "he": "רמות עוצמה (X = יחידת בסיס × מכפיל)",
            "en": "Magnitude Levels (X = base_unit × multiplier)",
        },
        "legend_title": {"he": "מקרא", "en": "Legend"},
        "legend_note": {
            "he": "התא מציג בחירה בודדת בעוצמה זו. כחול = הקטנה מרוכזת בפרויקט היעד; כתום = הקטנה מחולקת שווה בשווה בין שני הפרויקטים האחרים (היעד גדל).",
            "en": "Cell shows a single choice at that magnitude. Blue = concentrated decrease in the target; Orange = decrease split evenly across the other two (target increases).",
        },
        "legend_concentrated_desc": {
            "he": "הקטנה מרוכזת בפרויקט היעד (כל ההקטנה נלקחת ממנו; האחרים גדלים בשווה)",
            "en": "Concentrated decrease in the target project (entire decrease from target; the other two increase equally)",
        },
        "legend_distributed_desc": {
            "he": "הקטנה מבוזרת על פני שני הפרויקטים האחרים (מחולקת שווה בשווה; היעד גדל)",
            "en": "Distributed decrease across the other two projects (split evenly; target increases)",
        },
        "target_category": {"he": "קטגוריית יעד", "en": "Target Category"},
        "magnitude_level": {"he": "רמת עוצמה", "en": "Magnitude Level"},
        "decrease_preference": {"he": "מעדיף הקטנה", "en": "Prefers Decrease"},
        "increase_preference": {"he": "מעדיף הגדלה", "en": "Prefers Increase"},
        "color_legend_title": {"he": "מקרא צבעים", "en": "Color Legend"},
        "data_summary_title": {"he": "סיכום נתונים", "en": "Data Summary"},
        # Ranking survey translations
        "question": {"he": "שאלה", "en": "Question"},
        "ranking_instructions": {
            "he": "אנא דרגו את האפשרויות לפי העדפתכם (1 = הכי מועדף, 3 = הכי פחות מועדף)",
            "en": "Please rank the options by your preference (1 = most preferred, 3 = least preferred)",
        },
        "rank_1": {"he": "דירוג 1", "en": "Rank 1"},
        "rank_2": {"he": "דירוג 2", "en": "Rank 2"},
        "rank_3": {"he": "דירוג 3", "en": "Rank 3"},
        "most_preferred": {"he": "הכי מועדף", "en": "Most preferred"},
        "least_preferred": {"he": "הכי פחות מועדף", "en": "Least preferred"},
        "select_option": {"he": "בחרו אפשרות", "en": "Select option"},
        # Preference Ranking Consistency Analysis
        "user_preference_consistency_analysis": {
            "he": "ניתוח עקביות העדפות המשתמש",
            "en": "User Preference Consistency Analysis",
        },
        "table_preference_a_vs_b": {
            "he": "טבלה: העדפה א לעומת ב",
            "en": "Table: Preference A vs B",
        },
        "table_preference_a_vs_c": {
            "he": "טבלה: העדפה א לעומת ג",
            "en": "Table: Preference A vs C",
        },
        "table_preference_b_vs_c": {
            "he": "טבלה: העדפה ב לעומת ג",
            "en": "Table: Preference B vs C",
        },
        "final_ranking_summary_table": {
            "he": "טבלת סיכום דירוג סופי",
            "en": "Final Ranking Summary Table",
        },
        "positive_question": {
            "he": "שאלה +",
            "en": "Question +",
        },
        "positive_question_tooltip": {
            "he": "שאלות עם עוצמה חיובית - העדפות מוצגות כפי שהמשתמש בחר",
            "en": "Questions with positive magnitude - preferences shown as user chose them",
        },
        "negative_question": {
            "he": "שאלה –",
            "en": "Question –",
        },
        "negative_question_tooltip": {
            "he": "שאלות עם עוצמה שלילית - העדפות מוחלפות כדי לשקף משמעות אמיתית",
            "en": "Questions with negative magnitude - preferences swapped to reflect true meaning",
        },
        "row_consistency": {
            "he": "עקביות שורה",
            "en": "Row Consistency",
        },
        "column_consistency": {
            "he": "עקביות עמודה",
            "en": "Col. Cons.",
        },
        "final_score": {
            "he": "ניקוד סופי",
            "en": "Final Score",
        },
        "magnitude_0_2": {
            "he": "עוצמה 0.2",
            "en": "Magnitude 0.2",
        },
        "magnitude_0_4": {
            "he": "עוצמה 0.4",
            "en": "Magnitude 0.4",
        },
        "magnitude": {
            "he": "עוצמה",
            "en": "Magnitude",
        },
        # Consistency explanation translations
        "consistency_explanation_title": {
            "he": "הבנת ציוני העקביות",
            "en": "Understanding Consistency Scores",
        },
        "consistency_explanation_text": {
            "he": "ניתוח זה מודד עד כמה המשתמש מדרג באופן עקבי את אותם נושאי תקציב במצבים שונים. עקביות מושלמת (✓) פירושה שהמשתמש תמיד מדרג נושאים באותה צורה (3/3). עקביות חלקית (◐) פירושה שהמשתמש מראה עקביות בחלק מהמצבים אך משתנה באחרים (1/3 או 2/3). עקביות נכשלת (✗) פירושה שהדירוגים של המשתמש משתנים משמעותית (0/3). הערה: בשאלות עם עוצמה שלילית (שאלה –), העדפות המשתמש מוחלפות כדי לשקף את המשמעות האמיתית של בחירותיו.",
            "en": "This analysis measures how consistently the user ranks the same budget subjects across different scenarios. Perfect consistency (✓) means the user always ranks subjects the same way (3/3). Partial consistency (◐) means the user shows consistency in some scenarios but varies in others (1/3 or 2/3). Failed consistency (✗) means the user's rankings vary significantly (0/3). Note: In questions with negative magnitude (Question –), user preferences are swapped to reflect the true meaning of their choices.",
        },
        "perfect_consistency_label": {
            "he": "עקביות מושלמת",
            "en": "Perfect Consistency",
        },
        "partial_consistency_label": {
            "he": "עקביות חלקית",
            "en": "Partial Consistency",
        },
        "failed_consistency_label": {
            "he": "לא עקבי",
            "en": "Inconsistent",
        },
        "consistency_tooltip": {
            "he": "עקביות: ✓ = מושלמת (3/3), ◐ = חלקית (1-2/3), ✗ = לא עקבי (0/3)",
            "en": "Consistency: ✓ = Perfect (3/3), ◐ = Partial (1-2/3), ✗ = Failed (0/3)",
        },
        "final_score_tooltip": {
            "he": "ניקוד סופי: 1 = הכל עקבי, 0 = חלק לא עקבי",
            "en": "Final Score: 1 = All Consistent, 0 = Some Inconsistent",
        },
        # Preference swapping explanation
        "preference_swapping_explanation_title": {
            "he": "הסבר על החלפת העדפות בשאלות שליליות",
            "en": "Understanding Preference Swapping in Negative Questions",
        },
        "preference_swapping_explanation_text": {
            "he": "בשאלות עם עוצמה שלילית (שאלה –), העדפות המשתמש מוחלפות כדי לשקף את המשמעות האמיתית של בחירותיו. כאשר משתמש בוחר אפשרות א' על פני ב' בשאלה שלילית, זה אומר שהוא מעדיף להקטין את תקציב א' ולהגדיל את תקציב ב', ולכן הוא למעשה מעדיף ב' על א' מבחינת העדפות התקציב הבסיסיות שלו.",
            "en": "In questions with negative magnitude (Question –), user preferences are swapped to reflect the true meaning of their choices. When a user chooses option A over B in a negative question, it means they prefer to decrease A's budget and increase B's budget, so they actually prefer B over A in terms of their underlying budget allocation preferences.",
        },
        "positive_question_explanation": {
            "he": "שאלה +: העדפות מוצגות כפי שהמשתמש בחר",
            "en": "Question +: Preferences shown as user chose them",
        },
        "negative_question_explanation": {
            "he": "שאלה –: העדפות מוחלפות כדי לשקף משמעות אמיתית",
            "en": "Question –: Preferences swapped to reflect true meaning",
        },
        # Triangle inequality analysis
        "triangle_concentrated": {"he": "שינוי מרוכז", "en": "Concentrated Change"},
        "triangle_distributed": {"he": "שינוי מבוזר", "en": "Distributed Change"},
        "triangle_consistency": {
            "he": "עקביות משתמש",
            "en": "User Consistency",
        },
        "triangle_analysis_title": {
            "he": "ניתוח אי-שוויון המשולש",
            "en": "Triangle Inequality Analysis",
        },
        "prefers_concentrated": {
            "he": "מעדיפים שינוי מרוכז",
            "en": "Prefers Concentrated",
        },
        "prefers_distributed": {
            "he": "מעדיפים שינוי מבוזר",
            "en": "Prefers Distributed",
        },
        "triangle_explanation": {
            "he": "הטבלה מציגה את ההעדפות המשתמש בין שינויים מרוכזים (כל השינוי בשנה אחת) לעומת שינויים מבוזרים (שינויים בשתי השנים).",
            "en": "This table shows the user's preferences between concentrated changes (all change in one year) versus distributed changes (changes across both years).",
        },
    },
    "headers": {
        "comparison_pair": {"he": "זוג להשוואה", "en": "Comparison Pair"},
        "dominant_preference": {
            "he": "העדפה דומיננטית",
            "en": "Dominant Preference",
        },
        "consistent_groups": {"he": "קבוצות עקביות", "en": "Consistent Groups"},
    },
    "tables": {
        "pairwise_consistency_title": {
            "he": "עקביות זוגות",
            "en": "Pairwise Consistency",
        },
        "pairwise_consistency_caption": {
            "he": "הטבלה מסכמת את עקביות הבחירות בין כל זוגות האפשרויות על פני כל קבוצות האחוזונים.",
            "en": "This table summarizes the consistency of choices for each pair of options across all percentile groups.",
        },
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
