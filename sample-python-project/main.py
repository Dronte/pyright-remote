from greeting import WelcomeStringBuilder, Greeter


if __name__ == '__main__':
    welcome_string_builder = WelcomeStringBuilder('hello', 'world')
    greeter = Greeter(welcome_string_builder)
    greeter.greet()
