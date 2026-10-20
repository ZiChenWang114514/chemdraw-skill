import sys
sys.path.insert(0, r"C:\Users\mic23\cdxml-toolkit")
from cdxml_toolkit.perception.reaction_parser import parse_reaction
import inspect
print(inspect.signature(parse_reaction))
print(inspect.getdoc(parse_reaction)[:500] if inspect.getdoc(parse_reaction) else "No docstring")
