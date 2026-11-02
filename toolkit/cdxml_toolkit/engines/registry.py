"""What each engine is, where it comes from and what it needs. Standard library only.

``requirements`` are the versions verified together on macOS arm64. A ``weights`` entry names a
download that happens at install time; its sha256 is checked and written to a receipt. Nothing from
an engine is stored in this repository.
"""

from __future__ import annotations

MOLNEXTR_COMMIT = '6f6502b4ed9733dba8b1ee45d2da474576683194'
MOLPARSER_COMMIT = '8b67a082355a8fcf3b099e0e95c5ad948cbd7dcd'
MOLPARSER_WEIGHTS_REVISION = '6b3cbae494e6870252cb218865ae01fc8aaa55dc'

ENGINES = {
    'decimer-api': {
        'title': 'DECIMER (remote)', 'task': 'ocsr', 'kind': 'remote', 'license': 'MIT (service by the Steinbeck Lab)',
        'note': 'The default image-recognition engine; uploads the image after preflight (see decimer-api.md).',
    },
    'decimer-local': {
        'title': 'DECIMER (local)', 'task': 'ocsr', 'kind': 'runtime', 'module': 'DECIMER', 'license': 'MIT',
        'note': 'Runs in the runtime itself (extra: decimer); weights come from install_decimer_models.',
    },
    'molscribe': {
        'title': 'MolScribe', 'task': 'ocsr', 'kind': 'local', 'license': 'MIT', 'python': (10, 10),
        'module': 'molscribe',
        'requirements': ['molscribe==1.1.1', 'numpy<2', 'huggingface_hub'],
        'weights': {'repo': 'yujieq/MolScribe', 'type': 'model', 'files': ['swin_base_char_aux_1m.pth'],
                    'sha256': {'swin_base_char_aux_1m.pth':
                               '6f0df56fa32b5ffc21f8c7f311ef333da522f590bf5622e966c6bcb1f2d9ea1d'}},
        'size': '0.8 GB environment, 1.1 GB weights',
    },
    'molnextr': {
        'title': 'MolNexTR', 'task': 'ocsr', 'kind': 'local', 'license': 'Apache-2.0', 'python': (10, 10),
        'module': 'MolNexTR',
        'requirements': [f'MolNexTR @ git+https://github.com/CYF2000127/MolNexTR@{MOLNEXTR_COMMIT}',
                         'numpy<2', 'huggingface_hub'],
        'weights': {'repo': 'CYF200127/MolNexTR', 'type': 'dataset', 'files': ['molnextr_best.pth'],
                    'sha256': {'molnextr_best.pth':
                               '5990bc19aaafa5cf44e9d04e06fb8e2b5aea50c66e1e925f662bdff7d2a6422c'}},
        'size': '1.5 GB environment, 1.1 GB weights',
        'note': 'Installed from a pinned commit; weights are loaded with torch weights_only.',
    },
    'molparser': {
        'title': 'MolParser', 'task': 'ocsr', 'kind': 'local', 'license': 'Apache-2.0 (code); CC BY-NC-SA 4.0 (weights)',
        'python': (10, 12), 'module': 'molparser',
        'requirements': [f'molparser @ https://github.com/dptech-corp/MolParser/archive/{MOLPARSER_COMMIT}.tar.gz#sha256=a2985311661811a4ed57762a5636fee8ede3018e78e23b46fbc0cba4122a0c2e',
                         'torch', 'transformers', 'timm', 'safetensors', 'huggingface_hub', 'opencv-python-headless',
                         'numpy', 'pillow'],
        'weights': {'repo': 'UniParser/MolParser-Mobile-V2', 'type': 'model', 'revision': MOLPARSER_WEIGHTS_REVISION,
                    'files': ['config.json', 'generation_config.json', 'image_processing_molparser_mobile.py', 'modeling_molparser_mobile.py', 'preprocessor_config.json', 'processing_molparser_mobile.py', 'processor_config.json', 'tokenization_molparser_mobile.py', 'tokenizer_config.json', 'vocab.txt', 'model.safetensors'],
                    'sha256': {
                               'config.json':
                               'bb4b58b3b5e4e0db94af12569171b98737b0866c17aae2aad76ffe5f83e38e84',
                               'generation_config.json':
                               '9d51ec7c3bde6ce383fe05dcf346aa047db11a8c37133f96a86ad80e0e8b582c',
                               'image_processing_molparser_mobile.py':
                               'c64cbdc618c41f16a5c69d037697c112e8a44e969d3ad92f5605562069950b38',
                               'modeling_molparser_mobile.py':
                               'b95eb024613114b26968769964b37f2517277e4250d9e7e5fd61fdcf9b0bd065',
                               'preprocessor_config.json':
                               '2a70bd084b5e8bcd8fe9e58f08e96ae53740b78c9b5d2af6881ee7a8b15e0db9',
                               'processing_molparser_mobile.py':
                               '0109cde7457c78e8401c3b10f4670e7f71eb781d2f0202408cb1e4c111954d3d',
                               'processor_config.json':
                               'df03c932442eb3917cc486162895eb5fd789d9c93d933fce92301eb40fb876d3',
                               'tokenization_molparser_mobile.py':
                               'ea33f3484caf2d8da6f67b959a324e71b78050d8a6b07d935b9ea7ab22bac6f3',
                               'tokenizer_config.json':
                               '889fcbf784f1ea9eaef57f32758c972a4bebcaeab3bb2b57c2226e58c161ff83',
                               'vocab.txt':
                               '891652d9889d68eaaa8b27d490c0a966108e9da5689e67a9473cf5304b3e88fb',
                               'model.safetensors':
                               '2204a871f7975780ead6eee8ac354de11f859c4eccc8863c3462e6f9eb110f02',
                    }},
        'size': '1.5 GB environment, 20 MB weights',
        'note': 'Reads Markush and extended structures; only the base SMILES is used. The weights are licensed '
                'for non-commercial use only (CC BY-NC-SA 4.0). The model repository ships Python files that '
                'transformers runs on load; they are pinned by hash. The YOLO detector (ultralytics, AGPL) is '
                'not installed.',
    },
    'molvec': {
        'title': 'MolVec', 'task': 'ocsr', 'kind': 'jar', 'license': 'Apache-2.0',
        'jar': {'url': 'https://repo1.maven.org/maven2/gov/nih/ncats/molvec/0.9.8/'
                       'molvec-0.9.8-jar-with-dependencies.jar',
                'name': 'molvec-0.9.8.jar',
                'sha256': '7012c1fa602e54c68bbac60d3ea737b400b698ba60e99c7bb0beffc88ebe2b19'},
        'size': '1.3 MB (needs Java)',
    },
    'decimer-segmentation': {
        'title': 'DECIMER Segmentation', 'task': 'segmentation', 'kind': 'local', 'license': 'MIT',
        'python': (10, 11), 'module': 'decimer_segmentation',
        'requirements': ['decimer-segmentation==1.6.0', 'numpy<2'],
        'data': 'decimer-segmentation-model',
        'download': {'url': 'https://zenodo.org/record/10663579/files/mask_rcnn_molecule.h5?download=1',
                     'path': 'DECIMER-Segmentation_model/mask_rcnn_molecule.h5', 'sha256': '329120facb69e88add819a3216db0fbfef57e9a37d6b6db0f6149819a11d46a5'},
        'size': 'TensorFlow 2.14 environment (1.6 GB) and a 0.3 GB model',
    },
    'aizynthfinder': {
        'title': 'AiZynthFinder', 'task': 'retrosynthesis', 'kind': 'local', 'license': 'MIT',
        'python': (10, 12), 'module': 'aizynthfinder',
        'requirements': ['aizynthfinder', 'pyarrow<20'],
        'data': 'aizynthfinder-public-data',
        'size': '1.0 GB environment, 0.8 GB public data (USPTO policies, ZINC stock)',
    },
    'synplanner': {
        'title': 'SynPlanner', 'task': 'retrosynthesis', 'kind': 'local', 'license': 'MIT', 'python': (10, 12),
        'module': 'synplan',
        'requirements': ['SynPlanner[cpu]==1.7.0'],
        'data': 'synplanner-preset',
        'sha256': {
            'policy/supervised_gps/v1/reaction_rules.tsv':
                '46a34d9b59c8b9917808fdb7f99640afd8e0ff697e4964e7d18226c8fac6b382',
            'policy/supervised_gps/v1/v1/ranking_policy.ckpt':
                '01cf37995b55a308ac285ce14d98196893673f0383f85d370afa01286d7cc7c7',
            'policy/supervised_gcn/v1/v1/filtering_policy.ckpt':
                'a0d7e93690b447fae65d04af7ea5cdf1058d2831110dbb49b4d11ed2570e0f96',
            'value/supervised_gcn/v1/value_network.ckpt':
                'dbace1da49c1d400f43f667f6e6691a869472835461218d958803c001c0ea34c',
            'building_blocks/mcule-molport-2026-08/building_blocks.json.gz':
                '0fea071b828e70baa8012216d91e929f896951329509ce8af6c93c136b57eb81'},
        'size': '1.4 GB environment, 0.6 GB preset (MCULE/Molport building blocks, USPTO rules)',
        'note': 'Plans whole routes only (steps="multi"). Its checkpoints are PyTorch files from the project, '
                'checked against pinned hashes before use.',
    },
    'reactiont5-forward': {
        'title': 'ReactionT5v2 (products)', 'task': 'products', 'kind': 'local', 'license': 'MIT',
        'python': (10, 12), 'module': 'transformers', 'family': 'reactiont5',
        'requirements': ['torch', 'transformers==4.40.2', 'tokenizers==0.19.1', 'sentencepiece', 'numpy<2'],
        'weights': {'repo': 'sagawa/ReactionT5v2-forward', 'type': 'model', 'snapshot': True},
        'size': 'PyTorch environment, about 0.3 GB weights',
    },
    'reactiont5-retro': {
        'title': 'ReactionT5v2 (retrosynthesis)', 'task': 'retrosynthesis', 'kind': 'local', 'license': 'MIT',
        'python': (10, 12), 'module': 'transformers', 'family': 'reactiont5',
        'requirements': ['torch', 'transformers==4.40.2', 'tokenizers==0.19.1', 'sentencepiece', 'numpy<2'],
        'weights': {'repo': 'sagawa/ReactionT5v2-retrosynthesis', 'type': 'model', 'snapshot': True},
        'size': 'PyTorch environment, about 0.3 GB weights',
    },
    'magnet': {
        'title': 'MagNET', 'task': 'nmr', 'kind': 'local', 'license': 'MIT', 'python': (12, 12),
        'module': 'magnet',
        'requirements': ['torch==2.5.0', 'magnet-nmr', 'rdkit', 'huggingface_hub'],
        'find_links': 'https://data.pyg.org/whl/torch-2.5.0+cpu.html',
        'extra_requirements': ['torch_scatter', 'torch_cluster'],
        'weights': {'repo': 'ekwan16/MagNET', 'type': 'model', 'snapshot': True, 'include': 'model_checkpoints/*'},
        'elements': ['H', 'C', 'N', 'O', 'F', 'Cl', 'S'],
        'size': 'PyTorch environment',
    },
}

TASKS = ('ocsr', 'segmentation', 'products', 'retrosynthesis', 'conditions', 'nmr')


def by_task(task: str) -> list:
    return [name for name, spec in ENGINES.items() if spec['task'] == task]


# --- when an engine is worth installing -----------------------------------------------------------------
# ``disk_mb`` is the measured folder size of a finished install on macOS arm64 (rounded up). Nothing here
# downloads anything: it is what the Skill reads to recommend an engine, with its size, before the user agrees.

GUIDE = {
    'molscribe': {'disk_mb': 2000, 'use_when': 'a second opinion on a structure image, good on clean and mid-quality drawings',
                  'skip_when': 'the default DECIMER read is already confirmed against the image'},
    'molnextr': {'disk_mb': 2400, 'use_when': 'hard drawings with wedges and ring stereochemistry, as an extra vote',
                 'skip_when': 'two other engines already agree and the image checks out'},
    'molparser': {'disk_mb': 1100, 'use_when': 'Markush or extended structures, and as a third vote',
                  'skip_when': 'the work is commercial (its weights are non-commercial) or the structure is plain'},
    'molvec': {'disk_mb': 2, 'use_when': 'a rule-based second opinion that errs differently from the neural models; tiny',
               'skip_when': 'photographs, hand drawings or scans (it needs clean line art)', 'needs': ['java']},
    'decimer-segmentation': {'disk_mb': 2000, 'use_when': 'many structures on PDF pages that must be cut out and read',
                             'skip_when': 'one structure in one image (the OpenCV segmenter is enough for clean pages)'},
    'aizynthfinder': {'disk_mb': 1800, 'use_when': 'multi-step routes to purchasable starting materials',
                      'skip_when': 'a single quick guess at precursors is enough'},
    'synplanner': {'disk_mb': 2500, 'use_when': 'a second route planner with its own building-block list',
                   'skip_when': 'AiZynthFinder already gave a usable route'},
    'reactiont5-forward': {'disk_mb': 1600, 'use_when': 'ranked candidate products for given reactants',
                           'skip_when': 'the product is known or only needs an atom-balance check'},
    'reactiont5-retro': {'disk_mb': 1600, 'use_when': 'quick single-step precursor ideas',
                         'skip_when': 'AiZynthFinder is installed (it is more reliable)'},
    'magnet': {'disk_mb': 1300, 'use_when': 'predicted 1H and 13C shifts of one molecule',
               'skip_when': 'measured spectra are available (those are plotted without a model)'},
}

BUNDLES = {
    'ocsr-lite': {'engines': ['molvec'], 'task': 'ocsr',
                  'about': 'a tiny rule-based second opinion (needs Java)'},
    'ocsr-standard': {'engines': ['molscribe', 'molvec'], 'task': 'ocsr',
                      'about': 'two engines that err differently, enough for a comparison'},
    'ocsr-full': {'engines': ['molscribe', 'molnextr', 'molparser', 'molvec'], 'task': 'ocsr',
                  'about': 'every local OCSR engine, for hard drawings and Markush structures'},
    'pdf': {'engines': ['decimer-segmentation', 'molscribe', 'molvec'], 'task': 'pdf',
            'about': 'cut the structures out of PDF pages and read them with two engines'},
    'products': {'engines': ['reactiont5-forward'], 'task': 'products', 'about': 'candidate products of a reaction'},
    'retro': {'engines': ['aizynthfinder'], 'task': 'retro', 'about': 'single and multi-step retrosynthesis'},
    'nmr': {'engines': ['magnet'], 'task': 'nmr', 'about': 'predicted 1H and 13C shifts'},
}

# What to suggest for a need: the smallest set that does the job first, then larger alternatives.
RECOMMEND = {'ocsr': ['ocsr-standard', 'ocsr-lite', 'ocsr-full'], 'pdf': ['pdf'], 'products': ['products'],
             'retro': ['retro'], 'nmr': ['nmr']}


def disk_mb(names) -> int:
    return sum(GUIDE.get(name, {}).get('disk_mb', 0) for name in names)
