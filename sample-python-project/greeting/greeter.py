from dataclasses import dataclass


@dataclass
class WelcomeStringBuilder:
    greeting: str
    addressee: int  # intentional type annontation error to check pyright

    def get_welcome_string(self) -> str:
        #  due to type anootation error above 
        #  pyright will report error on this line
        return self.greeting.capitalize() + ', ' + self.addressee + '!'


class Greeter:
    def __init__(self, welcome_string_builder: WelcomeStringBuilder):
        self.welcome_string = welcome_string_builder.get_welcome_string()

    def greet(self)->None:
        print(self.welcome_string)
        
