def patch_file():
    path = "/Users/liozakirav/Documents/Projects/budget-survey/application/routes/survey_responses.py"
    with open(path, "r") as f:
        content = f.read()

    target = """                elif sort_by == "duration":
                    # Handle None values by putting them at the end
                    def get_duration(x):
                        val = x.get("total_response_time_seconds")
                        return float(val) if val is not None else (float('-inf') if reverse else float('inf'))
                    user_choices.sort(key=get_duration, reverse=reverse)"""

    replacement = """                elif sort_by == "duration":
                    # Handle None values by putting them at the end
                    def get_duration(x):
                        val = x.get("total_response_time_seconds")
                        return float(val) if val is not None else (float('-inf') if reverse else float('inf'))
                    user_choices.sort(key=get_duration, reverse=reverse)
                    
                    # region agent log
                    import json
                    with open("/Users/liozakirav/Documents/Projects/budget-survey/.cursor/debug-363d07.log", "a") as f:
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
                    # endregion"""

    if target in content:
        content = content.replace(target, replacement)
        with open(path, "w") as f:
            f.write(content)
        print("Patched successfully")
    else:
        print("Target not found")


patch_file()
