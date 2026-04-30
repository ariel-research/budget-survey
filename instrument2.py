def patch_file():
    path = "/Users/liozakirav/Documents/Projects/budget-survey/analysis/presentation/html_renderers.py"
    with open(path, "r") as f:
        content = f.read()

    target = """        sorted_summaries = sorted(
            survey_summaries, key=lambda x: x.get(sort_key, "") or "", reverse=reverse
        )"""

    replacement = """        sorted_summaries = sorted(
            survey_summaries, key=lambda x: x.get(sort_key, "") or "", reverse=reverse
        )
        
        # region agent log
        import json
        with open("/Users/liozakirav/Documents/Projects/budget-survey/.cursor/debug-363d07.log", "a") as f:
            f.write(json.dumps({
                "sessionId": "363d07",
                "hypothesisId": "H1",
                "location": "html_renderers.py:generate_detailed_breakdown_table",
                "message": "Sorted summaries",
                "data": {
                    "sort_by": sort_by, 
                    "sort_key": sort_key, 
                    "reverse": reverse,
                    "order": [(s["user_id"], str(s.get(sort_key, ""))) for s in sorted_summaries]
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
