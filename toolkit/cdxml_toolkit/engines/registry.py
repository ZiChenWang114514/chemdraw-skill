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
        'extra': 'decimer', 'size': '1.5 GB of packages in the runtime (TensorFlow), 0.7 GB weights',
        'note': 'Runs in the runtime itself: installing adds the toolkit extra "decimer" (TensorFlow) to the runtime '
                'and the DECIMER weights to DECIMER_MODEL_DIR (default ~/.data/DECIMER-V2).',
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
        'requirements': ['aizynthfinder==4.4.1', 'pyarrow<20'],
        'data': 'aizynthfinder-public-data',
        'sha256': {  # the files config.yml names; config.yml itself holds local paths and is not pinned
            'uspto_model.onnx': 'bd0a3cb74cd7068de474c8fb789a00a66bc42c75636d66510ccac585ebe928f8',
            'uspto_templates.csv.gz': 'a4f1945e90cfa195538320833d68aed38f14e2fcc2f8afb5d958bc920edcafbe',
            'uspto_ringbreaker_model.onnx': '1bf0690352d9e9212d7dbe8b35649caf74f73ef0b30edefdfdac37fce38085be',
            'uspto_ringbreaker_templates.csv.gz': '5616a056454b10a2f044e69e027422128986856ebd958541a3bf9f837e3a0d14',
            'uspto_filter_model.onnx': 'ad29aa32bdfcbe37065045546493806cf04899c55386c438905d83fb14bb6320',
            'zinc_stock.hdf5': '99d39a6f807c3e815487500bafc2b4a9dc66a31af189e3b1776874fb0d4a188d',
        },
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
        'weights': {'repo': 'sagawa/ReactionT5v2-forward', 'type': 'model', 'snapshot': True,
                    'revision': '933114058cb2604dc1bf536dbebdfcefbe83d4fc'},
        'size': 'PyTorch environment, about 0.3 GB weights',
    },
    'reactiont5-retro': {
        'title': 'ReactionT5v2 (retrosynthesis)', 'task': 'retrosynthesis', 'kind': 'local', 'license': 'MIT',
        'python': (10, 12), 'module': 'transformers', 'family': 'reactiont5',
        'requirements': ['torch', 'transformers==4.40.2', 'tokenizers==0.19.1', 'sentencepiece', 'numpy<2'],
        'weights': {'repo': 'sagawa/ReactionT5v2-retrosynthesis', 'type': 'model', 'snapshot': True,
                    'revision': '4ba688b3ed597b137a78610b1a1dff42784eb60c'},
        'size': 'PyTorch environment, about 0.3 GB weights',
    },
    'magnet': {
        'title': 'MagNET', 'task': 'nmr', 'kind': 'local', 'license': 'MIT', 'python': (12, 12),
        'module': 'magnet',
        'requirements': ['torch==2.5.0', 'magnet-nmr==0.2.1', 'rdkit', 'huggingface_hub'],
        'find_links': 'https://data.pyg.org/whl/torch-2.5.0+cpu.html',
        'extra_requirements': ['torch_scatter', 'torch_cluster'],
        'weights': {'repo': 'ekwan16/MagNET', 'type': 'model', 'snapshot': True, 'include': 'model_checkpoints/*',
                    'revision': 'fe222d1894afb2d954fe8d2e67e70731a006c8d2'},
        'elements': ['H', 'C', 'N', 'O', 'F', 'Cl', 'S'],
        'size': 'PyTorch environment',
    },
    'retrochimera': {
        'title': 'RetroChimera + Syntheseus', 'task': 'retrosynthesis', 'kind': 'local', 'license': 'MIT',
        'python': (10, 10), 'module': 'retrochimera',
        'requirements': ['torch==2.2.2', 'torch_geometric==2.5.2', 'pytorch-lightning==2.2.2', 'torchmetrics<0.11', 'h5py',
                         'scipy<1.12', 'rdkit', 'numpy<2', 'pebble~=5.2.0', 'loky', 'omegaconf', 'more_itertools', 'tqdm',
                         'pandas', 'networkx', 'setuptools<81', 'retrochimera==1.3.0', 'syntheseus==0.9.0'],
        'data': 'retrochimera-pistachio',
        'zip_members': {
            'url': 'https://api.figshare.com/v2/file/download/59468882',
            'members': [
                {'match': ['models.json'], 'path': 'models.json', 'sha256': 'f9d5e152b7fb4713bf5df802aa6f5ddd1141adce164ca404965bd620a79e68ac'},
                {'match': ['template_localization/combined.ckpt'], 'path': 'template_localization/combined.ckpt',
                 'sha256': '4deac13c05c050eb66a78f46692e32704dac45c426937ca2274017cab637304c'},
                {'match': ['template_localization/template_lib.json'], 'path': 'template_localization/template_lib.json',
                 'sha256': '2238c363a29b0ffd8a54524d5223eff31e383d69bb1c87d0d738afcad2f8e9d6'},
                {'match': ['smiles_transformer/combined.ckpt'], 'path': 'smiles_transformer/combined.ckpt',
                 'sha256': 'f6013a4cc078614df687c603d252584497b9a3fc480b0d3e57f5c0f199ea92b2'},
                {'match': ['smiles_transformer/vocab.txt'], 'path': 'smiles_transformer/vocab.txt', 'sha256': '96f751c4cafa8724a0d7bc940421b95dad7a9b82da433bb29371a677b98e4e22'}]},
        'stock': {'url': 'https://huggingface.co/Laboratoire-De-Chemoinformatique/SynPlanner-data/resolve/main/'
                         'building_blocks/mcule-molport-2026-08/building_blocks.json.gz',
                  'path': 'building_blocks/building_blocks.json.gz',
                  'sha256': '0fea071b828e70baa8012216d91e929f896951329509ce8af6c93c136b57eb81'},
        'size': '0.7 GB environment, 4.7 GB model (Pistachio ensemble), 0.5 GB building blocks; the model is a 4.2 GB '
                'download and building the stock list takes about 15 minutes',
        'note': "Microsoft Research's RetroChimera (Nature 2026) with the Syntheseus search. Single step (steps=\"single\") "
                'or whole routes (steps="multi"). The authors state it is for research and experiments: an expert must '
                'check every route, and lower-ranked reactions are more likely to be hallucinated.',
    },
    'nmrnet-pp': {
        'title': 'NMRNet++', 'task': 'nmr', 'kind': 'local', 'license': 'MIT', 'python': (11, 11), 'module': 'unicore',
        'requirements': ['torch==2.5.1', 'numpy', 'setuptools<81', 'wheel', 'rdkit', 'lmdb', 'pandas', 'scikit-learn',
                         'scipy', 'joblib', 'tqdm', 'ml_collections', 'tensorboardX'],
        'late_requirements': ['https://github.com/dptech-corp/Uni-Core/archive/ace6fae1c8479a9751f2bb1e1d6e4047427bc134.tar.gz'
                              '#sha256=ae240ff27dfc4c698081260d58ce4bee30d4f437fef23bed89d4033625f21583'],
        'data': 'nmrnet-pp',
        'downloads': [{'url': 'https://github.com/YongqiJin/NMRNetplusplus/archive/'
                              '3ba8b9c2f3d0a390d00685d238618345c6ab24d7.tar.gz',
                       'path': 'code.tar.gz', 'sha256': 'e074c870b642790483eb0e65b23451901ee40bcfa8905e2721b1b2c8dc1580e6',
                       'extract': 'tar.gz', 'into': 'code'}],
        'zip_members': [
            {'url': 'https://zenodo.org/records/18232165/files/checkpoints.zip?download=1',
             'members': [
                 {'match': ['scratch_H_pretraining_molecular_unimol_large_atom_regloss_mae_lr_0.0004_bs1_4_bs2_16_wu_0.03_ep_10_wgt_16_T__ratio_4_16_20250930_033837', 'fold_0/checkpoint_last.pt'], 'path': 'H/cv_seed_42_fold_0/checkpoint_last.pt',
                  'sha256': 'bc12977a19ddad7057c8c4d190203cdae8130b52e54f3ddbf37d875663de04e9'},
                 {'match': ['scratch_H_pretraining_molecular_unimol_large_atom_regloss_mae_lr_0.0004_bs1_4_bs2_16_wu_0.03_ep_10_wgt_16_T__ratio_4_16_20250930_033837', 'target_scaler.ss'], 'path': 'H/target_scaler.ss',
                  'sha256': 'dfd9201d59b0beadc11b4e9b98c4ac8e3dbf0724ccd3408e77488b62f718cc41'},
                 {'match': ['scratch_C_pretraining_molecular_unimol_large_atom_regloss_mae_lr_0.0004_bs1_4_bs2_16_wu_0.03_ep_10_wgt_16_T__ratio_4_16_20251004_182236', 'fold_0/checkpoint_last.pt'], 'path': 'C/cv_seed_42_fold_0/checkpoint_last.pt',
                  'sha256': '888c2fdcdd0379ded4c6de7322414fcf98658f4092adf8687a54329643c0376a'},
                 {'match': ['scratch_C_pretraining_molecular_unimol_large_atom_regloss_mae_lr_0.0004_bs1_4_bs2_16_wu_0.03_ep_10_wgt_16_T__ratio_4_16_20251004_182236', 'target_scaler.ss'], 'path': 'C/target_scaler.ss',
                  'sha256': '8d9af306251634c2c064e4a61ba0f71344d8569573c7d517b25b4cf42678a39b'}]},
            {'url': 'https://zenodo.org/records/18232165/files/weight.zip?download=1',
             'members': [{'match': ['weight/dict.txt'], 'path': 'weight/dict.txt',
                          'sha256': 'f4fafdbc445449c8f8ef613fee36c8ee7610e3c7c2766666635edc8d962ba134'}]}],
        'elements': ['H', 'C', 'N', 'O', 'S', 'Cl', 'F', 'Br', 'I', 'Si', 'P', 'B'],
        'size': '0.8 GB environment, about 1.2 GB checkpoints',
        'note': 'ICML 2026; one of its five cross-validation checkpoints per nucleus (fold 0) is used, so it is a single '
                'model, not the published ensemble. The authors include DP Technology staff; no company affiliation '
                'is claimed here.',
    },
    'reacon': {
        'title': 'Reacon', 'task': 'conditions', 'kind': 'local',
        'license': 'not declared by the authors (no LICENSE file in their repository)',
        'python': (10, 10), 'module': 'torch',
        'requirements': ['torch==2.5.1', 'chemprop==1.6.1', 'torch-geometric==2.3.0', 'pandas==1.5.3', 'numpy<2', 'setuptools<81', 'rdkit'],
        'data': 'reacon',
        'downloads': [{'url': 'https://github.com/wzhstat/Reaction-Condition-Selector/archive/'
                              'aeedf1b8682d5b61f2ee3ea5a987fdd0c571c7b0.tar.gz',
                       'path': 'code.tar.gz', 'sha256': '28031acb05f16dde46096ca96107ac4727f26b16099236d80f504fed192150f7',
                       'extract': 'tar.gz', 'into': 'code'}],
        'archive_members': {
            'url': 'https://www.dropbox.com/scl/fo/v1rhyes2wvead9dz3x4fb/h?rlkey=nqtst7azldcry3ixnoigmcv3v&dl=1',
            'members': [
                {'name': 'USPTO_condition/data/condition_library/condition_library_r1.json.gz',
                 'path': 'condition_library/condition_library_r1.json.gz',
                 'sha256': 'cf40e8c5a105f1a2845ec4e4ab2d779ac915f714361cd47a57c8735355f49eb6'},
                {'name': 'USPTO_condition/data/condition_library/condition_library_r0.json.gz',
                 'path': 'condition_library/condition_library_r0.json.gz',
                 'sha256': 'bb8e86e1c363bc61c8ded75f435e97b23922d7f29fa9dab34d6764c3922dcba1'},
                {'name': 'USPTO_condition/data/condition_library/condition_library_r0_1.json.gz',
                 'path': 'condition_library/condition_library_r0_1.json.gz',
                 'sha256': 'c86a86f3aa57d3a785049917561a51d1895bb5fcb79d1b341b3f38a85e81f014'}]},
        'size': '1.0 GB environment, 0.14 GB repository with trained models, 0.12 GB condition libraries (a 2 GB '
                'download from the authors, deleted after the libraries are taken out)',
        'note': "Chem. Sci. 2025. The authors' repository states no licence, so the code and models are not "
                'redistributed here: they are downloaded from the authors at a pinned commit, on request.',
    },
}

TASKS = ('ocsr', 'segmentation', 'products', 'retrosynthesis', 'conditions', 'nmr')


def by_task(task: str) -> list:
    return [name for name, spec in ENGINES.items() if spec['task'] == task]


# --- when an engine is worth installing -----------------------------------------------------------------
# ``disk_mb`` is the measured folder size of a finished install on macOS arm64 (rounded up). Nothing here
# downloads anything: it is what the Skill reads to recommend an engine, with its size, before the user agrees.

GUIDE = {
    'decimer-local': {'disk_mb': 2300, 'use_when': 'the DECIMER reading is wanted but the image may not be uploaded',
                      'skip_when': 'uploading is allowed: the DECIMER API runs the same model'},
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
    'retrochimera': {'disk_mb': 5900, 'use_when': 'the strongest single-step precursor suggestions available here, '
                                                  'and routes searched with them',
                     'skip_when': 'a quick idea is enough (AiZynthFinder is much smaller), or the work needs a commercial '
                                  'licence check first: the authors state research use only'},
    'nmrnet-pp': {'disk_mb': 1900, 'use_when': 'a second opinion on predicted 1H and 13C shifts, including Br, I, Si, P and B',
                  'skip_when': 'measured spectra are available (those are plotted without a model)'},
    'reacon': {'disk_mb': 1100, 'use_when': 'candidate catalysts, solvents and reagents for a reaction already drawn',
               'skip_when': 'the conditions are in the source, or the reaction type is new (it learned from patents); '
                            "its authors' repository declares no licence"},
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
    'decimer-local': {'engines': ['decimer-local'], 'task': 'ocsr',
                      'about': 'the DECIMER model on this computer, for images that may not be uploaded (TensorFlow)'},
    'pdf': {'engines': ['decimer-segmentation', 'molscribe', 'molvec'], 'task': 'pdf',
            'about': 'cut the structures out of PDF pages and read them with two engines'},
    'products': {'engines': ['reactiont5-forward'], 'task': 'products', 'about': 'candidate products of a reaction'},
    'retro': {'engines': ['aizynthfinder'], 'task': 'retro', 'about': 'single and multi-step retrosynthesis'},
    'nmr': {'engines': ['magnet'], 'task': 'nmr', 'about': 'predicted 1H and 13C shifts'},
    'nmr-pp': {'engines': ['nmrnet-pp'], 'task': 'nmr', 'about': 'a second NMR model to compare with MagNET'},
    'retro-chimera': {'engines': ['retrochimera'], 'task': 'retro',
                      'about': 'RetroChimera single-step suggestions and Syntheseus route search (research use)'},
    'conditions': {'engines': ['reacon'], 'task': 'conditions', 'about': 'candidate reaction conditions (unlicensed code)'},
}

# What to suggest for a need: the smallest set that does the job first, then larger alternatives.
RECOMMEND = {'ocsr': ['ocsr-standard', 'ocsr-lite', 'ocsr-full', 'decimer-local'], 'pdf': ['pdf'], 'products': ['products'],
             'retro': ['retro', 'retro-chimera'], 'nmr': ['nmr', 'nmr-pp'], 'conditions': ['conditions']}
# Engine task names that differ from the need they are recommended under.
RECOMMEND_ALIASES = {'retrosynthesis': 'retro', 'segmentation': 'pdf'}


def disk_mb(names) -> int:
    return sum(GUIDE.get(name, {}).get('disk_mb', 0) for name in names)
