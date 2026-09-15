"""Generate both illustrative publication layouts into new directories."""
from pathlib import Path
import argparse
from cdxml_toolkit.mcp_runtime.publication_figure import publication_figure

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    for mode in ('scope','sar'):
        result=publication_figure('create',str(Path(__file__).parent/(mode+'.json')),str(args.output/mode))
        print(mode,result['status'],result['output_dir'])

if __name__=='__main__':main()
