from simulation import Engine
from parser import Parser
import logging

logging.basicConfig(level=logging.DEBUG, filename="debug.log")


def main() -> None:
    filepath = "maps/challenger/01_the_impossible_dream.txt"
    parser = Parser(filepath)
    program = Engine(filepath)
    program.run()
    


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        

