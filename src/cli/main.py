import sys

def main():
    print("Wpisz 'exit' lub 'quit' by zakończyć działanie programu")
    while True:
        try:
            cli = input("Dzień dobry: ")

            if cli == "quit" or cli == "exit":
                print("Użytkownik kończy działanie programu")
                break
            
            if cli.strip() == "":
                continue

            print(f"You said: {cli}")
        except KeyboardInterrupt:
            print("Uzytkownik zakończył działanie programu")
            sys.exit(0)

if __name__ == "__main__":
    main()
