def patch_file():
    path = "/Users/liozakirav/Documents/Projects/budget-survey/application/routes/survey_responses.py"
    with open(path, "r") as f:
        content = f.read()

    target = """                    # region agent log
                    import json
                    import os
                    log_dir = "/Users/liozakirav/Documents/Projects/budget-survey/.cursor"
                    if not os.path.exists(log_dir):
                        try:
                            os.makedirs(log_dir, exist_ok=True)
                        except Exception:
                            pass
                    
                    log_path = "/Users/liozakirav/Documents/Projects/budget-survey/.cursor/debug-363d07.log"
                    try:
                        with open(log_path, "a") as f:
                            f.write(json.dumps({
                                "sessionId": "363d07",
                                "hypothesisId": "H1",
                                "location": "survey_responses.py:get_user_responses",
                                "message": "Sorted user_choices",
                                "data": {
                                    "sort_by": sort_by,
                                    "reverse": reverse,
                                    "order": [(c["user_id"], c.get("total_response_time_seconds")) for c in user_choices[:10]]
                                }
                            }) + "\\n")
                    except Exception as e:
                        print(f"DEBUG LOG ERROR: {e}")
                    # endregion"""

    replacement = ""

    if target in content:
        content = content.replace(target, replacement)
        with open(path, "w") as f:
            f.write(content)
        print("Removed instrumentation from survey_responses.py")
    else:
        print("Instrumentation not found in survey_responses.py")


patch_file()
