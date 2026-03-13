import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from study_demo.main import run

if __name__ == "__main__":
    run()
