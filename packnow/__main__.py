try:
    from .main import main
except ImportError:
    print("Please use this as a module, which is python -m")
    exit()

if __name__ == "__main__":
    main()
