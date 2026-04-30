def patch_file():
    path = "/Users/liozakirav/Documents/Projects/budget-survey/analysis/presentation/html_renderers.py"
    with open(path, "r") as f:
        content = f.read()

    target = """        key_map = {"user_id": "user_id", "created_at": "response_created_at"}
        sort_key = key_map.get(sort_by, "response_created_at")
        reverse = (sort_order.lower() == "desc") if sort_by else True"""

    replacement = """        key_map = {"user_id": "user_id", "created_at": "response_created_at"}
        sort_key = key_map.get(sort_by, "response_created_at")
        reverse = (sort_order.lower() == "desc") if sort_by else True
        
        # region agent log
        import json
        with open("/Users/liozakirav/Documents/Projects/budget-survey/.cursor/debug-363d07.log", "a") as f:
            f.write(json.dumps({
                "sessionId": "363d07",
                "hypothesisId": "H1",
                "location": "html_renderers.py:generate_detailed_breakdown_table",
                "message": "Sorting params",
                "data": {"sort_by": sort_by, "sort_order": sort_order, "sort_key": sort_key, "reverse": reverse}
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
