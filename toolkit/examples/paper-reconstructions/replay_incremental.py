"""Replay the reviewed twenty-structure fixture; source recognition is not repeated."""
import argparse
from pathlib import Path
from cdxml_toolkit.mcp_runtime import reconstruction as r


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_image',help='Authorized source screenshot used for visual review')
    parser.add_argument('output',help='New directory; existing files are never replaced')
    parser.add_argument('--native',action='store_true',help='Run fresh dual-reader checks and native previews')
    args=parser.parse_args()
    case=Path(__file__).resolve().parents[2]/'assets/readme/stereo-reconstruction'
    evidence=r._read(case/'verification.json')
    if r._hash(args.source_image)!=evidence['source_sha256']:
        raise ValueError('This regression fixture requires its original source image; do not infer correspondence')
    output=Path(args.output).resolve()
    if output.exists(): raise ValueError('Use a new output directory')
    output.mkdir(parents=True)
    target=r._target([{'label':x['label'],'smiles':x['smiles']} for x in evidence['molecules']],
        'Reviewed source target recorded in the published twenty-structure fixture.',True)
    r._write(output/'target.json',target)
    snapshots=[]
    for name,file in [('source','source-oriented.cdxml'),('compatible','reconstruction.cdxml')]:
        snapshot=r._capture(str(case/file),args.source_image,transform={'scale':[2,2],'offset':[0,0]},
            context={'Ar':'PMP'},versions={'fixture':'reviewed_twenty_structure_case'})
        snapshots.append(snapshot);r._write(output/(name+'-snapshot.json'),snapshot)
    r._write(output/'changes.json',r._plan(*snapshots))
    if args.native:
        result=r._verify_variants(str(case/'source-oriented.cdxml'),str(case/'reconstruction.cdxml'),target,str(output/'dual'))
        for name in ('source','compatible'):
            r._overlay(args.source_image,str(output/'dual'/(name+'-render')/(name+'.png')),str(output/(name+'-overlay')),[30,10])
        print(r._json({'output':str(output),'acceptance':result['acceptance']}))
    else:
        print(r._json({'output':str(output),'acceptance':'not_evaluated','native':'not_run'}))


if __name__=='__main__':
    main()
