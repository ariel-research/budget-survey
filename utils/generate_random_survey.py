from generate_examples import (
    create_random_vector,
    generate_user_example,
    get_user_vector_str,
)


def html_survey(user_vector, user_examples, file_name):
    user_vector_html = "<h4>"
    subjects = ["ביטחון", "חינוך", "בריאות"]
    for i in range(len(user_vector)):
        user_vector_html += f"{user_vector[i]} - {subjects[i]}\n"
    user_vector_html += "</h4>"
    html = """
    <html dir='rtl' style='font-family:"Noto Sans Hebrew", sans-serif;'>
    <head>
        <meta charset="UTF-8">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@300;400&display=swap" rel="stylesheet">

    </head>
    <body>
        <h1>סקר חלוקת תקציב</h1>
        <h2>יש לך תקציב של 100 לחלק בין שלושה משרדים: משרד הבטחון, משרד החינוך, משרד הבריאות. איך היית מחלק/ת?</h2>
        <h3>בהנחה שהחלוקה שבחרת היא:</h3>
        <h3 dir='ltr' style='text-align: right;'>{user_vector}</h3>
        {user_vector_html}
        <h3>אנא ענה/עני על השאלות הבאות:</h3>
    """.format(
        user_vector=user_vector, user_vector_html=user_vector_html
    )

    for i, question in enumerate(user_examples, start=1):
        html += f"<p>{i}. מבין שתי חלוקות התקציב הבאות, איזו עדיפה לדעתך?</p>\n"
        html += (
            '<input type="radio" name="question{}" value="Option 1">{}<br>\n'.format(
                i, question[0]
            )
        )
        html += (
            '<input type="radio" name="question{}" value="Option 2">{}<br>\n'.format(
                i, question[1]
            )
        )
    html += "</body></html>"
    with open(f"examples/{file_name}.html", "w") as file:
        file.write(html)


def survey(user_vector, html):
    """
    Generate a survey for a given user vector and optionally output it as an HTML file.

    Parameters:
    user_vector (tuple): The user-provided vector to use as a basis for the survey.
    html (bool): A flag indicating whether to generate an HTML output of the survey.

    Returns:
    list[tuple[tuple]]: A list of tuples representing the edges of the generated graph.
    """
    file_name = f"user{get_user_vector_str(user_vector)}"
    user_examples = generate_user_example(user_vector)
    if html:
        html_survey(user_vector, user_examples, file_name)
    return user_examples


def n_surveys(n=1, html=False):
    """
    Generate multiple surveys for a given number of users and optionally output them as HTML files.

    Parameters:
    n (int): The number of surveys to generate.
    html (bool): A flag indicating whether to generate HTML outputs of the surveys.

    Returns:
    dict: A dictionary where keys are user vectors and values are lists of tuples representing
    the edges of the generated graphs for each user.

    This function generates `n` user-specific surveys using the `survey` function.
    It ensures unique user vectors for each survey and stores the generated examples
    in a dictionary.

    Example:
    >>> surveys = n_surveys(2, html=True)
    >>> print(surveys)
    """
    users = dict()
    while len(users) < n:
        user_vector = create_random_vector()
        while user_vector in users:
            user_vector = create_random_vector()
        user_examples = survey(user_vector, html)
        users[user_vector] = list(user_examples)

    return users
