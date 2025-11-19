import os
import re


def clean_filename(name):
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = re.sub(r"_{2,}", "_", name)
    return name.lower()


folder = "downloads/"

for filename in os.listdir(folder):
    old_path = os.path.join(folder, filename)
    new_name = clean_filename(filename)
    new_path = os.path.join(folder, new_name)
    os.rename(old_path, new_path)
