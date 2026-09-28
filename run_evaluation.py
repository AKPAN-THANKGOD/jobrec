"""Run the Chapter 4 evaluation and save the output to evaluation_results.txt.

Usage:
    python run_evaluation.py
The file `evaluation_results.txt` is written next to this script.
"""
import io
import contextlib
from datetime import datetime

import evaluate  # your existing module


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        evaluate.run()
    output = buf.getvalue()

    header = (
        "=" * 72 + "\n"
        "SkillMatch — Chapter 4 evaluation results\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "=" * 72 + "\n\n"
    )
    with open("evaluation_results.txt", "w", encoding="utf-8") as fh:
        fh.write(header + output)
    print("Wrote evaluation_results.txt")
    print(output)


if __name__ == "__main__":
    main()