import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    {
        "name": "Listening",
        "script": os.path.join(BASE_DIR, "listening", "run_live.py"),
        "cwd": os.path.join(BASE_DIR, "listening")
    },
    {
        "name": "Reading",
        "script": os.path.join(BASE_DIR, "reading", "run_live.py"),
        "cwd": os.path.join(BASE_DIR, "reading")
    },
    {
        "name": "Writing",
        "script": os.path.join(BASE_DIR, "writing ow1", "run_live.py"),
        "cwd": os.path.join(BASE_DIR, "writing ow1")
    }
]

def run_course():
    print("=" * 75)
    print(" BHARAT ENGLISH - AUTONOMOUS FULL COURSE RUNNER")
    print(" Sequential Pipeline: Listening (30) -> Reading (30) -> Writing (30)")
    print(" Press Ctrl+C at any time to pause or exit.")
    print("=" * 75)

    for step in STEPS:
        name = step["name"]
        script_path = step["script"]
        cwd = step["cwd"]

        if not os.path.exists(script_path):
            print(f"\n[Error] Could not find script for {name}: {script_path}")
            continue

        print("\n" + "#" * 75)
        print(f" >>> [STAGE START] Running {name.upper()} (All 30 Modules) <<<")
        print("#" * 75 + "\n")

        # Run the step in a subprocess using the current Python executable
        ret_code = subprocess.run([sys.executable, script_path], cwd=cwd).returncode

        if ret_code != 0:
            print(f"\n[Warning] {name} exited with code {ret_code}.")
            choice = input(f"Do you want to continue to the next skill? (y/n, default y): ").strip().lower()
            if choice == "n":
                print("\n[Exiting] Stopped by user.")
                return
        else:
            print(f"\n[Success] {name} module completed all 30 lessons!")

        print("\nCooling down for 5 seconds before next section...")
        time.sleep(5)

    print("\n" + "=" * 75)
    print(" 🎉 CONGRATULATIONS! ALL 3 SKILLS (LISTENING, READING, WRITING) ARE FINISHED! 🎉")
    print("=" * 75)

if __name__ == "__main__":
    run_course()
