def patch_file():
    path = "/Users/liozakirav/Documents/Projects/budget-survey/analysis/presentation/html_renderers.py"
    with open(path, "r") as f:
        content = f.read()

    target = """        # region agent log
        import json
        import os
        log_dir = "/Users/liozakirav/Documents/Projects/budget-survey/.cursor"
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                pass
        
        # In Docker, the path might be different, let's try a relative path or stdout fallback
        log_path = "/Users/liozakirav/Documents/Projects/budget-survey/.cursor/debug-363d07.log"
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({
                    "sessionId": "363d07",
                    "runId": "post-fix",
                    "hypothesisId": "H1",
                    "location": "html_renderers.py:generate_detailed_breakdown_table",
                    "message": "Final sorted summaries",
                    "data": {
                        "sort_by": sort_by, 
                        "sort_key": sort_key, 
                        "reverse": reverse,
                        "order": [(s["user_id"], s.get("choices", [{}])[0].get("total_response_time_seconds")) for s in sorted_summaries]
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
        print("Removed instrumentation from html_renderers.py")
    else:
        print("Instrumentation not found in html_renderers.py")


patch_file()
