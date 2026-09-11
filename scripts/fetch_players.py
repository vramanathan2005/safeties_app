"""Export recruits from the UCReport API."""
from ucreport_pipeline import main

if __name__ == "__main__":
    main(kind='recruits', append=False)
