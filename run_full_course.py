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

    for idx, step in enumerate(STEPS):
        name = step["name"]
        script_path = step["script"]
        cwd = step["cwd"]

        if not os.path.exists(script_path):
            print(f"\n[Error] Could not find script for {name}: {script_path}")
            continue

        print("\n" + "#" * 75)
        print(f" >>> [STAGE {idx+1}/3] STARTING {name.upper()} (All 30 Modules) <<<")
        print("#" * 75 + "\n")

        # Run each module in non-blocking unbuffered mode
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        ret_code = subprocess.run([sys.executable, "-u", script_path], cwd=cwd, env=env).returncode

        if ret_code != 0:
            print(f"\n[Notice] {name} module step finished with code {ret_code}. Moving to next section...")
        else:
            print(f"\n[Success] {name} module completed 100%!")

        print("\nCooling down for 3 seconds before next skill...")
        time.sleep(3)

    print("\n" + "=" * 75)
    print(" 🎉 ALL 3 SKILLS (LISTENING, READING, WRITING) ARE FINISHED! 🎉")
    print("=" * 75)

if __name__ == "__main__":
    run_course()
