from generate_examples import generate_user_example


if __name__=="__main__":
    user_vector = (10, 20, 70)
    examples = generate_user_example(user_vector, plot=True, save_txt=True)