"""COO Interface script entry point.

Run a single COO query from the command line and print the structured response.
Useful for testing the interface and for future Telegram/Chat integration.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commerceos.config.settings import get_settings
from commerceos.coo.interface import ask_coo
from commerceos.platform.database.connection import get_session


def main():
    parser = argparse.ArgumentParser(description="Ask the CommerceOS COO Interface a question")
    parser.add_argument("query", nargs="?", default="What matters today?", help="Natural-language question")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    args = parser.parse_args()

    settings = get_settings()
    session = get_session(settings.database_url)
    try:
        result = ask_coo(session, args.query)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(result["answer"])
            if result.get("warnings"):
                print("\nWarnings:")
                for w in result["warnings"]:
                    print(f"- {w}")
            if result.get("suggested_actions"):
                print("\nSuggested actions:")
                for a in result["suggested_actions"]:
                    print(f"- {a}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
