import urllib.request, subprocess, sys, pathlib

pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)
try:
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
        "data/raw/results.csv",
    )
    subprocess.run([sys.executable, "pipelines/train.py"], check=True)
    print("Training complete")
except Exception as e:
    print(f"Training skipped: {e}")
