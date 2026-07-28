from simulation import Engine
from pathlib import Path
from terminal_outputs import rainbow_text
from pathfinding import ScheduleError
from sys import stderr
from shutil import get_terminal_size


def main() -> None:
    """Present a menu of available map files, prompt for a selection
    (or a custom filepath), then run the simulation on the chosen map.

    Re-prompts on invalid input rather than exiting, clearing the
    screen between attempts.
    """
    map_list = sorted(Path("maps").rglob("*.txt"))
    map_dict = {i + 1: map_path for i, map_path in enumerate(map_list)}
    while True:
        print("\033[H\033[J")
        terminal_width = get_terminal_size().columns
        welcome_text = rainbow_text(
            " Welcome to Fly-in! ".center(terminal_width, '='))
        print(welcome_text)
        print("\nMap List:\n")

        for i, map_path in map_dict.items():
            print(f"{i}: {map_path}")

        print(f"{len(map_list) + 1}: Custom map path")
        print()
        print(f"{rainbow_text(''.center(terminal_width,'='))}")
        print()
        selection = input("Select your map: ")

        try:
            map_choice = int(selection)
        except ValueError:
            print(f"Non-numeric value: {selection}", file=stderr)
            input("Press ENTER to continue...")
            continue
        if map_choice < 1 or map_choice > len(map_list) + 1:
            print(f"Invalid numeric value: {map_choice}", file=stderr)
            input("Press ENTER to continue...")
            continue
        elif map_choice == len(map_list) + 1:
            filepath = input("Input custom filepath <path/file.txt>: ")
            if not Path(filepath).is_file():
                print(f"Map file not found: {filepath}", file=stderr)
                input("Press ENTER to continue...")
                continue
            elif Path(filepath).suffix.lower() != ".txt":
                print("Invalid file format: *.txt expected", file=stderr)
                input("Press ENTER to continue...")
                continue
            else:
                break
        else:
            filepath = str(map_dict[map_choice])
            break
    print("\033[H\033[J")
    program = Engine(filepath)
    program.run()


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\nValue Error: {e}")
    except (FileNotFoundError, PermissionError,
            IsADirectoryError, NotADirectoryError) as e:
        print(f"\nFile Error: {e}")
    except EOFError:
        print("\nCTRL + D detected. Exiting program")
    except KeyboardInterrupt:
        print("\nCTRL + C detected. Exiting program")
    except ScheduleError as e:
        print(f"\nSchedule Error: {e}")
    except AssertionError as e:
        print(f"\nInternal Consistency Error: {e}")
    except Exception as e:
        print(f"\nGeneral exception thrown: {e}")
