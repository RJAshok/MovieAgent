import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.query_data.query_data import query_data

res = query_data("SELECT budget, worldwide_gross FROM movies WHERE movie_name = 'Project Hail Mary'")
print("Result:", res)
