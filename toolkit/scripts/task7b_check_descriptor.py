import sys
sys.path.insert(0, r"C:\Users\mic23\cdxml-toolkit")
from cdxml_toolkit.perception.reaction_parser import ReactionDescriptor
import inspect
# Check how to save / convert to JSON
print(dir(ReactionDescriptor))
print()
# Check if it has a to_json or save method
for attr in dir(ReactionDescriptor):
    if not attr.startswith('_'):
        print(attr)
