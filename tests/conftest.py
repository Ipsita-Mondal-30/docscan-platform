import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ["DOCSCAN_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["DOCSCAN_UPLOAD_DIR"] = "/tmp/docscan-test-uploads"
