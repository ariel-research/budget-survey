from generate_examples import generate_user_example, create_random_vector

def survey(users_size, file_name="survey"):
    html = "<html><body>"
    html += "<h1>Survey for Education, Health and Economic</h1>"

    users = set()
    
    while (len(users)<users_size):
        user_vector = create_random_vector()
        while user_vector in users:
            user_vector = create_random_vector()
        users.add(user_vector)
        html += f"<h2>User {user_vector}</h2>"
        user_examples = generate_user_example(user_vector)
        for i, question in enumerate(user_examples, start=1):
            html += f"<p>{i}: Choose your preference</p>"
            html += '<input type="radio" name="question{}" value="Option 1">{}<br>'.format(i,question[0])
            html += '<input type="radio" name="question{}" value="Option 2">{}<br>'.format(i,question[1])
        html += "</body></html>"

    with open(f"surveys/{file_name}.html", "w") as file:
        file.write(html)

survey(5)