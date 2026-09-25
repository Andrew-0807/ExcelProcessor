import os
import sys

# onedir layout: the exe sits in the same folder as app/ and scripts/.
if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(sys.executable)))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.launcher import main

if __name__ == "__main__":
    main()
