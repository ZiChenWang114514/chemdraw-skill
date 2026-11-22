# Reviewed Exclusions Public Symbols

> Generated from cdxml-toolkit 0.8.0. Curated guidance: [reviewed-exclusions.md](reviewed-exclusions.md).

## `acs_builder`

- **function**, line 691: `build_from_spec(spec_path, output_path = None)` - Build a CDXML from a JSON spec (or dict); coordinates are points, x right, y down.
- **class**, line 178: `Fig` - No public docstring in the audited version.
- **method**, line 605: `Fig.add_conformer(spec_or_template, **kwargs)` - Insert a 3D conformer or projection template from cdxml_toolkit.templates.conformers.
- **method**, line 576: `Fig.add_interaction(p1, p2, style = 'dashed', color = 'jacs_blue', label = None, clip_margin = 3.5)` - Draw an endpoint-clipped dashed line for H-bonds, pi-stacking, or TS partial bonds.
- **method**, line 552: `Fig.add_orbital(cx, cy, orbital_type = 'pShaded', angle_deg = -90.0, length = 18.0, width = 7.5, color = 'jacs_blue')` - Emit a native CDXML <graphic GraphicType="Orbital"> lobe at (cx, cy).
- **method**, line 519: `Fig.add_ts_bracket(box, superscript = '‡', bracket_type = 'Square', lip_size = 5.0, object_ids = None)` - Emit left and right Square bracket graphics, <bracketedgroup>, and top-right superscript (e.g. double dagger).
- **method**, line 497: `Fig.arrow(x1, y1, x2, y2, kind = 'forward')` - No public docstring in the audited version.
- **method**, line 504: `Fig.box(x1, y1, x2, y2, round_ = True)` - No public docstring in the audited version.
- **method**, line 509: `Fig.label_box(x, y, markup, w = None)` - bold Arial code in a rounded box centred at (x,y)
- **method**, line 232: `Fig.mol(smiles, at = (100, 100), labels = None, coords = None, rotate = 0.0, flip = False, scale = BL, displays = None, radicals = (), wedge = True, explicitH = None, center = True, hide_charge_label = False, lone_pairs = (), double_pos = None, label_text = None, ring_fills = None, atom_halos = None, multi_attachments = None)` - smiles may contain [*:n] dummy atoms; labels maps n -> label text (e.g. 'C10H21'). coords: optional list of (x,y) in drawing units (y down) per atom index (overrides layout). displays: dict bond_idx -> CDXML Display (WedgeBegin etc., B = bond begin atom). label_text: dict atom_idx -> explicit label markup. ring_fills: optional list of {'ring_index': 0, 'color': 'pastel_blue', 'style': 'polygon'|'spline', 'inset': 1.0}. atom_halos: optional list of {'atoms': [0, 1], 'color': 'pastel_yellow', 'radius': 8.0}. multi_attachments: optional list of {'metal_atom': 0, 'ligand_atoms': [1..5], 'bond_display': 'Dash', 'bond_order': 'dative'}.
- **method**, line 195: `Fig.resolve_color(color)` - Resolve a JACS_PALETTE name, #RRGGBB hex string, or integer index into a CDXML colortable index.
- **method**, line 487: `Fig.text(x, y, markup, size = 10, align = 'Center', bold = False, font = 3, color = None)` - No public docstring in the audited version.
- **method**, line 669: `Fig.to_cdxml()` - No public docstring in the audited version.
- **method**, line 683: `Fig.write(path)` - Write the figure to a new file; FileExistsError if ``path`` exists.
- **function**, line 107: `formula_markup(label)` - C10H21 -> C{sub:10}H{sub:21}; leaves already-marked text alone
- **function**, line 87: `runs(markup, font = 3, size = 10, base = 0, color = None)` - No public docstring in the audited version.

## `atom_mapping`

- **function**, line 300: `available_methods() -> list` - Methods that can run now: the built-in one plus every installed learned backend.
- **function**, line 32: `hill(counts) -> str` - No public docstring in the audited version.
- **function**, line 585: `map_atoms(left, right, *, resolve_ambiguity: bool = False, method: str = 'auto', compare: bool = False) -> dict` - Map the heavy atoms of products ``right`` onto reactants ``left`` (lists of (label, mol)).
- **function**, line 531: `map_atoms_many(reactions, *, resolve_ambiguity: bool = False, method: str = 'auto', compare: bool = False) -> list[dict]` - Map many reactions at once; ``reactions`` is a list of ``(left, right)`` as in :func:`map_atoms`.

## `catalog.cdxml`

- **function**, line 100: `binary_names(paths: Iterable[Path], names: Iterable[str]) -> set[str]` - Names that occur as standalone ASCII strings in the given binaries.
- **function**, line 112: `build_catalog(observed: dict[str, Any], *, binary_names: set[str], candidates: Iterable[str] = CANDIDATES, fixtures: Optional[list[dict[str, Any]]] = None, verified_on: str = 'unverified') -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 267: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 244: `extract_live(workdir, *, verified_on: Optional[str] = None) -> dict[str, Any]` - Scan the CDXML ChemDraw installs, plus what it writes for the bundled CDX files and fixtures.
- **function**, line 54: `scan_documents(paths: Iterable[Path]) -> dict[str, Any]` - Collect elements, attributes, nesting and value shapes from CDXML files.
- **function**, line 41: `summarise_values(values: set[str]) -> dict[str, Any]` - Describe the shape of an attribute's observed values without keeping free text.

## `catalog.chemscript`

- **function**, line 87: `build_catalog(reflection: dict[str, Any], docs: dict[str, str], *, verified_on: str = 'unverified', bases: Optional[dict[str, str]] = None) -> dict[str, Any]` - Join a reflection dump (``include_infrastructure`` on) with XML summaries.
- **function**, line 204: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 188: `extract_live(reflection_path, *, verified_on: Optional[str] = None) -> dict[str, Any]` - Read the installed SDK (Windows) and build the catalog; ``reflection_path`` must not exist.
- **function**, line 40: `parse_xml_docs(path) -> dict[str, str]` - Map each ``T:``/``M:``/``P:``/``F:`` key of the SDK's XML docs to its one-line summary.
- **function**, line 175: `read_bases() -> dict[str, str]` - Full name of each exported type's base type, read in-process through Python.NET.

## `catalog.classify`

- **function**, line 185: `all_rows() -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 159: `classify(catalogs: dict[str, dict[str, Any]], recipes: list[dict[str, Any]], classification: dict[str, Any]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 192: `find_row(rows: Iterable[dict[str, Any]], row_id: str) -> Optional[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 29: `load_catalog(layer: str) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 33: `load_classification() -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 178: `summarize(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]` - No public docstring in the audited version.

## `catalog.com`

- **function**, line 212: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 189: `extract_live(*, verified_on: Optional[str] = None) -> dict[str, Any]` - Read the type libraries of the installed ChemDraw (Windows); ChemDraw is not started.
- **function**, line 71: `merge_properties(members: list[dict[str, Any]]) -> list[dict[str, Any]]` - Fold a property's get/put/putref accessors into one ``property`` member, in first-seen order.
- **function**, line 159: `read_typelib(path) -> dict[str, Any]` - Describe every type of the type library at ``path`` (an .exe, .dll, .ocx or .tlb).
- **function**, line 35: `type_name(desc, info) -> str` - Readable name of a TYPEDESC as pythoncom returns it: an int, or ``(vt, inner)``.

## `catalog.menu`

- **function**, line 24: `build_catalog(raw: list[dict[str, Any]], *, verified_on: str = 'unverified') -> dict[str, Any]` - Turn the raw ``[{menu, items: [{caption, command_id}]}]`` walk into the committed shape.
- **function**, line 108: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 82: `extract_live(*, verified_on: Optional[str] = None) -> dict[str, Any]` - Start a private ChemDraw (Windows), read its menus and quit it.
- **function**, line 57: `find_command(catalog: dict[str, Any], caption: str) -> Optional[tuple[str, int]]` - Return ``(menu caption, command id)`` for a menu item caption, ignoring case.

## `catalog.recipes`

- **function**, line 42: `check(recipe: dict[str, Any], results: list[dict[str, Any]]) -> list[str]` - Return one message per expectation the results do not meet.
- **function**, line 56: `declaring_type(catalog: dict[str, Any], type_name: str, member: str) -> Optional[str]` - The type of the ChemScript catalog that declares ``member``, following base types.
- **function**, line 68: `fill_program(program: list[dict[str, Any]], *, fixture: str, out: str) -> list[dict[str, Any]]` - Copy a COM recipe program with ``{fixture}`` and ``{out}`` replaced in every string.
- **function**, line 18: `load() -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 104: `run(recipe: dict[str, Any]) -> list[str]` - Execute a recipe on the installed ChemDraw and return its failures.

## `catalog.render`

- **function**, line 368: `lookup(layer: str, name: str, blocks: dict[str, list[tuple[str, str]]] | None = None) -> dict[str, Any]` - The block of the type called ``name``, or the type names that contain it.
- **function**, line 359: `member_blocks(catalogs: dict[str, dict[str, Any]] | None = None, recipes: list[dict[str, Any]] | None = None, classification: dict[str, Any] | None = None) -> dict[str, list[tuple[str, str]]]` - ``{layer: [(type name, Markdown block listing its members)]}`` for the layers that have members.
- **function**, line 351: `render_all(catalogs: dict[str, dict[str, Any]] | None = None, recipes: list[dict[str, Any]] | None = None, classification: dict[str, Any] | None = None) -> dict[str, str]` - No public docstring in the audited version.

## `characterization`

- **function**, line 113: `atoms_mass(mol) -> float` - Sum of the monoisotopic (or labelled-isotope) atom masses, without any electron correction.
- **function**, line 126: `default_adduct(mol, mode: str = 'positive', ionization: str = 'ESI') -> str` - No public docstring in the audited version.
- **function**, line 135: `hrms_entry(mol, adduct: str | None = '[M+H]+', *, ionization: str = 'ESI', decimals: int = 4, found: float | None = None, electron_mass: bool = True) -> dict` - {adduct, ion_formula, charge, calcd_mz, found_mz, error_ppm, line} for one ion of ``mol``.
- **function**, line 93: `ion_component(mol)` - (component, kept_charge) of a multi-component record: the organic ion of a salt.
- **function**, line 84: `organic_component(mol)` - The fragment with most carbons (then most heavy atoms); the molecule itself if it has one.

## `chemistry_diff`

- **function**, line 12: `core_mappings(a, b, query, limit: int = MAX_CORE_MAPPINGS)` - Every mapping of *query* matches in *a* onto those in *b*, or None past *limit*.
- **function**, line 93: `structural_diff(before: str, after: str, timeout: int = 5) -> dict` - No public docstring in the audited version.

## `chemistry_semantics`

- **function**, line 140: `document_inventory(path)` - No public docstring in the audited version.
- **function**, line 68: `read_fragment_element(fragment, *, sanitize = True, remove_hs = True)` - Molecules RDKit reads from one ``<fragment>`` element (a list; may be empty).
- **function**, line 74: `read_fragments(value)` - Top-level CDXML fragments as ``(fragment_id, mol)`` pairs, in document order.
- **function**, line 119: `read_molecules(value)` - No public docstring in the audited version.
- **function**, line 36: `require_supported(mol, *, allow_radicals: bool = False, allow_dative: bool = True, allow_atropisomers: bool = True)` - No public docstring in the audited version.
- **function**, line 10: `semantic_key(mol)` - No public docstring in the audited version.
- **function**, line 144: `validate_document_preserved(source, output)` - No public docstring in the audited version.
- **function**, line 123: `validate_fragment(smiles, xml, *, allow_radicals: bool = True)` - No public docstring in the audited version.

## `engines.accel`

- **function**, line 49: `accel_mode(mode: str | None = None) -> str` - ``'auto'``, ``'on'`` or ``'off'`` from ``mode`` or ``CHEMDRAW_ACCEL``.
- **function**, line 228: `active_daemons(engine_home: Path) -> list[dict[str, Any]]` - Resident daemons that are running, idle or busy (stale state files are pruned).
- **function**, line 261: `call_via_daemon(*, engine: str, python: Path, worker_script: Path, request: dict[str, Any], env_vars: dict[str, str], engine_home: Path, device_key: str, timeout: int) -> tuple[dict[str, Any], str] | None` - Execute ``request`` on a warm resident worker, spawning one if needed.
- **function**, line 79: `daemon_state_path(engine_home: Path, engine: str, device: str) -> Path` - The state file of the resident worker for ``engine`` on ``device`` (``'cpu'`` or any other device).
- **class**, line 95: `DaemonTimeout` - A resident worker accepted a request and did not answer within the caller's timeout.
- **function**, line 85: `idle_timeout_seconds() -> int` - No public docstring in the audited version.
- **function**, line 160: `probe_daemon(state_file: Path) -> tuple[str, dict[str, Any] | None]` - ``('live', info)``, ``('busy', info)`` (the worker is serving a request) or ``('gone', None)``.
- **function**, line 215: `stop_all_daemons(engine_home: Path) -> list[str]` - Shut down all warm resident engine daemons under ``engine_home`` and return their names.
- **function**, line 195: `stop_daemon_file(state_file: Path) -> bool` - No public docstring in the audited version.
- **function**, line 63: `wants_daemon(engine: str, action: str = 'predict', params: dict[str, Any] | None = None, *, mode: str | None = None) -> bool` - True when this engine call should run on a resident worker.

## `engines.consensus`

- **function**, line 313: `compare(entries: list, expected_formula: str | None = None) -> dict` - Group the engines by the structure they read.

## `engines.document`

- **function**, line 107: `extract(path: str, out_dir: str, pages = None, engines: str = 'molscribe,molvec', segmenter: str = 'auto', dpi: int = 200, confirm_upload: bool = False, hand_drawn: bool = False) -> dict` - Segment, recognize and compare. ``out_dir`` must be new or empty; nothing existing is overwritten.

## `engines.env`

- **function**, line 151: `available() -> dict` - Which engines can run now. Remote engines count as available; the network policy decides later.
- **function**, line 204: `call(name: str, action: str, params: dict, timeout: int = RUN_TIMEOUT) -> dict` - Run ``action`` of engine ``name`` in its environment and return the worker's ``result``.
- **function**, line 126: `configured_device(name: str) -> str` - The device ``name`` is configured to run on ('cuda', 'cpu', or 'remote').
- **function**, line 86: `data_dir(name: str) -> Path` - Where an engine's downloaded weights or data live (inside its own folder).
- **function**, line 601: `disk_usage(name: str) -> int` - Bytes used by the engine's own folder (0 when it has none). Symbolic links are not followed.
- **class**, line 39: `EngineError` - An engine is missing, could not run, or returned something unusable.
- **class**, line 43: `EngineMissing` - The engine is not installed. ``hint`` says what installing it would cost, for the user to decide.
- **function**, line 75: `environment(name: str) -> Path` - No public docstring in the audited version.
- **function**, line 51: `hint(name: str) -> dict` - What to tell the user when ``name`` is needed but absent: use, size, licence and the command.
- **function**, line 64: `home() -> Path` - No public docstring in the audited version.
- **function**, line 528: `install(name: str, *, dry_run: bool = False, log = None) -> dict` - Create the environment (or fetch the jar), install the pinned requirements and the weights.
- **function**, line 79: `interpreter(env: Path) -> Path | None` - No public docstring in the audited version.
- **function**, line 104: `jar_path(name: str) -> Path | None` - No public docstring in the audited version.
- **function**, line 91: `java() -> str | None` - No public docstring in the audited version.
- **function**, line 139: `last_call_meta(name: str | None = None) -> dict` - Device metadata from the most recent ``call`` on this context, or configured defaults.
- **function**, line 110: `python_for(name: str) -> Path | None` - The interpreter that runs engine ``name``, or None when it is not installed.
- **function**, line 96: `receipt(name: str) -> dict | None` - No public docstring in the audited version.
- **function**, line 654: `recommend(task: str) -> dict` - The smallest set of engines that serves ``task`` (a need in ``RECOMMEND`` or an engine task name), with what each costs. Reads only; nothing is downloaded.
- **function**, line 677: `remove(name: str, *, dry_run: bool = True) -> dict` - Delete one engine's folder. Only a direct child of ``home()`` that looks like an engine is removed.
- **function**, line 296: `run_jar(name: str, args: list, timeout: int = 300) -> subprocess.CompletedProcess` - No public docstring in the audited version.
- **function**, line 306: `sha256_of(path) -> str` - No public docstring in the audited version.
- **function**, line 634: `status(sizes: bool = False) -> dict` - Which engines are available and their disk use. Sizes come from the receipts; ``sizes=True`` measures again.

## `engines.envelope`

- **function**, line 8: `describe(smiles: str | None, score = None, **extra) -> dict` - A predicted structure: the engine's SMILES plus what RDKit can say about it.
- **function**, line 40: `failure(task: str, engine: str, spec: dict, error, **extra) -> dict` - ``error`` may be the exception itself: a missing engine then carries ``install_hint`` (what to ask the user).
- **function**, line 49: `molfile_to_smiles(molfile: str) -> str | None` - No public docstring in the audited version.
- **function**, line 30: `result(task: str, engine: str, spec: dict, structures = None, **extra) -> dict` - The envelope: ``ok`` is true when the engine ran, not when its answer is right.

## `engines.nmr`

- **function**, line 394: `compare_shifts(smiles: str, experimental_1h: list[float] | None = None, experimental_13c: list[float] | None = None, *, solvent: str = 'CDCl3', engines: Iterable[str] = ('magnet',), predicted_result: dict[str, Any] | None = None, outlier_threshold_1h: float = 0.5, outlier_threshold_13c: float = 5.0) -> dict[str, Any]` - Compare predicted NMR shifts against experimental 1H/13C peak lists using Hungarian matching.
- **function**, line 121: `predict(smiles: str, nucleus: str = '1H', solvent: str = 'chloroform', frequency_mhz: float = 400.0, engine: str | None = None, output_path: str | None = None, timeout_seconds: int = 900) -> dict` - ``engine`` may name several, comma separated: each runs and the peaks are compared, never merged. An engine that fails is listed in ``failed_engines`` and the others still answer.
- **function**, line 46: `simulate(peaks: list, nucleus: str, frequency_mhz: float, width_hz: float = 1.5, points: int = 16384) -> list` - Lorentzian singlets on a ppm axis (no coupling): a picture of where the lines fall, not a multiplet pattern.

## `engines.ocsr`

- **function**, line 85: `recognize(image_path: str, engines = 'decimer-api', hand_drawn: bool = False, output_path: str | None = None, timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: str | None = None, approved_origin: str | None = None, expected_formula: str | None = None) -> dict` - Run the chosen engines on one image. ``all`` means every installed local engine, plus the remote DECIMER only when ``confirm_upload`` is true. One engine failing never stops the others. ``output_path`` is a new JSON file for the raw response of the remote DECIMER; the local engines have none.
- **function**, line 117: `recognize_batch(image_paths: list[str], engines: str = 'molscribe,molvec', *, hand_drawn: bool = False, timeout_seconds: int = 600, confirm_upload: bool = False, approved_origin: str | None = None, expected_formula: str | None = None) -> list[dict]` - Run the chosen engines on a batch of images, calling each worker-backed engine once for the whole batch.
- **function**, line 12: `resolve(engines) -> list` - Engine names from ``"decimer-api"``, ``"molscribe,molvec"``, a list, or ``"all"`` (see ``recognize``).

## `engines.reactions`

- **function**, line 391: `build_route_comparison_cdxml(routes_by_engine: Any, output_path: str | Path | None = None, target_smiles: str | None = None) -> dict[str, Any]` - Render top retrosynthetic routes from multiple engines into a stacked-rows CDXML figure.
- **function**, line 508: `compare_retrosynthesis_routes(product: str, engines: Sequence[str] | str = ('aizynthfinder', 'synplanner', 'retrochimera'), max_steps: int = 6, top_k_per_engine: int = 2, output_cdxml: str | Path | None = None, time_limit: int = 60, timeout_seconds: int = 900) -> dict[str, Any]` - Run multiple retrosynthesis engines on `product` and optionally render a comparison CDXML figure.
- **function**, line 593: `conditions(reactants: str, products: str, engine: str | None = None, count: int = 5, timeout_seconds: int = 900) -> dict` - Rank catalyst, solvent and reagent combinations for a reaction the user already drew.
- **function**, line 42: `products(reactants: str, reagents: str | None = None, engine: str | None = None, count: int = 5, timeout_seconds: int = 600) -> dict` - Predict the products of ``reactants`` (dot-separated SMILES), optionally with ``reagents``.
- **function**, line 204: `retrosynthesis(product: str, engine: str | None = None, steps: str = 'single', count: int = 5, time_limit: int = 60, timeout_seconds: int = 900, output_cdxml: str | None = None) -> dict` - Suggest precursors (``steps='single'``) or whole routes (``'multi'``) for ``product``.

## `engines.registry`

- **function**, line 274: `by_task(task: str) -> list` - No public docstring in the audited version.
- **function**, line 344: `disk_mb(names) -> int` - No public docstring in the audited version.

## `engines.table`

- **function**, line 35: `bundles_table() -> str` - No public docstring in the audited version.
- **function**, line 46: `download_size(bundle: str) -> str` - What installing ``bundle`` takes on disk, from the registry's measured engine sizes: ``about 4.7 GB``.
- **function**, line 27: `engines_table() -> str` - No public docstring in the audited version.
- **function**, line 54: `render(text: str) -> str` - ``text`` with every marked table replaced by the one the registry gives, and every ``<!--size:BUNDLE-->`` span by that bundle's size; a missing marker is an error.

## `engines.worker`

- **function**, line 78: `fetch(engine, params, data_dir, spec)` - Download weights or data into ``data_dir`` and return a receipt (hashes, revisions).
- **function**, line 351: `remote_range(url, first, last)` - No public docstring in the audited version.
- **function**, line 1319: `spec_elements(params)` - No public docstring in the audited version.

## `mapping_backends`

- **function**, line 85: `available() -> dict` - No public docstring in the audited version.
- **class**, line 89: `BackendError` - A backend could not run or returned something unusable.
- **function**, line 62: `environment(name: str) -> Path` - No public docstring in the audited version.
- **function**, line 130: `find_base(name: str) -> str | None` - A Python that can host backend ``name``: this one, else python3.N on PATH, else the Windows launcher.
- **function**, line 50: `home() -> Path` - Folder that holds one environment per backend (CHEMDRAW_MAPPER_HOME overrides it).
- **function**, line 183: `install(name: str, *, dry_run: bool = False, log = None) -> dict` - Create ``environment(name)``, install its pinned requirements and check it with a real mapping.
- **function**, line 66: `interpreter(env: Path) -> Path | None` - No public docstring in the audited version.
- **function**, line 73: `python_for(name: str) -> Path | None` - Interpreter that can run backend ``name``: its own environment, else this one if it imports.
- **function**, line 93: `run(name: str, reactions: list, timeout: int = RUN_TIMEOUT) -> list` - Map reaction SMILES with backend ``name``; one dict per reaction (mapped_rxn plus a score).
- **function**, line 221: `status() -> dict` - No public docstring in the audited version.

## `mcp_runtime`

- **function**, line 11: `build_server(*args, **kwargs)` - Build the complete MCP server without importing it during package discovery.

## `mcp_runtime.artifact_safety`

- **function**, line 162: `apply_default_mode(path: str | Path) -> None` - Give a staged file the mode a plain open() would: mkstemp() files are 0600.
- **function**, line 276: `artifact_record(path: str | Path) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 289: `artifact_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **class**, line 20: `OutputExistsError` - An output already exists and the tool will not replace it.
- **property**, line 30: `OutputExistsError.public_message` - No public docstring in the audited version.
- **function**, line 301: `paths_from_value(value: Any) -> list[Path]` - No public docstring in the audited version.
- **function**, line 247: `publish_directory(staged: str | Path, destination: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 193: `publish_file(staged: str | Path, destination: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 231: `publish_files(staged_outputs: Iterable[tuple[Path, Path]]) -> None` - No public docstring in the audited version.
- **function**, line 71: `resolve_destination(*, source: str | Path | None, output_path: str | Path | None, tag: str, suffix: str, base_dir: str | Path | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 106: `resolve_directory_destination(*, source: str | Path, output_dir: str | Path | None, tag: str) -> Path` - No public docstring in the audited version.
- **function**, line 327: `rewrite_paths(value: Any, old_root: str | Path, new_root: str | Path) -> Any` - No public docstring in the audited version.
- **function**, line 346: `stage_validate_publish(destination: str | Path, writer: Callable[[Path], Any], *, validator: Callable[[Path], Any] = validate_artifact) -> tuple[Any, Path]` - No public docstring in the audited version.
- **function**, line 182: `staging_directory(destination: str | Path) -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 172: `staging_file(destination: str | Path) -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 126: `validate_artifact(path: str | Path) -> Path` - No public docstring in the audited version.
- **function**, line 34: `validate_input_file(path: str | Path, *, suffixes: tuple[str, ...] | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 319: `with_artifacts(result: dict[str, Any], paths: Iterable[str | Path]) -> dict[str, Any]` - No public docstring in the audited version.

## `mcp_runtime.capabilities`

- **function**, line 37: `get_toolkit_capabilities(detail: str = 'full') -> dict[str, Any]` - Return runtime identity and diagnostics; detail='summary' omits tool signatures.

## `mcp_runtime.chemistry_compare`

- **function**, line 265: `batch_compare_molecules(pairs: list[dict[str, Any]], fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, Any]` - Compare up to 256 molecule pairs with one ChemScript bridge session.
- **function**, line 203: `compare_molecules(molecule_a: str, molecule_b: str, fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, Any]` - Compare two molecule representations using ChemScript identity and RDKit Tanimoto fingerprints.

## `mcp_runtime.chemscript_sdk`

- **class**, line 58: `ChemScriptSdkUnavailable` - ChemScript SDK programs need Windows (the .NET SDK) or macOS (its emulation).
- **function**, line 183: `execute_chemscript_sdk(program: list[dict[str, Any]], allow_file_io: bool = False, allow_overwrite: bool = False, allow_unsafe_interop: bool = False, max_items: int = 100) -> dict[str, Any]` - Execute a declarative ChemScript SDK program in an isolated Python.NET process.
- **function**, line 125: `inspect_chemscript_sdk(query: Optional[str] = None, type_name: Optional[str] = None, include_infrastructure: bool = False, offset: int = 0, limit: int = 100, output_path: Optional[str] = None) -> dict[str, Any]` - Catalog every public ChemScript type/member, with filtering or a complete JSON export.

## `mcp_runtime.chemscript_sdk_mac`

- **class**, line 115: `Atom` - No public docstring in the audited version.
- **class**, line 137: `AtomMap` - Atom-to-atom map, keyed like a .NET dictionary (``Keys``, ``map[atom]``).
- **property**, line 148: `AtomMap.Count` - No public docstring in the audited version.
- **property**, line 144: `AtomMap.Keys` - No public docstring in the audited version.
- **class**, line 129: `Bond` - No public docstring in the audited version.
- **class**, line 398: `LargestCommonSubstructure` - No public docstring in the audited version.
- **method**, line 412: `LargestCommonSubstructure.AtomMapM1() -> AtomMap` - No public docstring in the audited version.
- **method**, line 415: `LargestCommonSubstructure.AtomMapM2() -> AtomMap` - No public docstring in the audited version.
- **method**, line 409: `LargestCommonSubstructure.CommonSubstructure() -> Optional[StructureData]` - No public docstring in the audited version.
- **method**, line 404: `LargestCommonSubstructure.Compute(first: StructureData, second: StructureData)` - No public docstring in the audited version.
- **class**, line 472: `MacSdkRuntime` - The program runtime interface of ``ChemScriptRuntime``, for the emulation.
- **method**, line 522: `MacSdkRuntime.catalog() -> tuple[list[dict], list[dict]]` - No public docstring in the audited version.
- **method**, line 510: `MacSdkRuntime.check_member(owner: Any, member: str, operation: str) -> None` - Refuse anything that is not an emulated public member (no Python internals).
- **method**, line 507: `MacSdkRuntime.member_is_interop(reflection_type, member: str) -> bool` - No public docstring in the audited version.
- **method**, line 486: `MacSdkRuntime.python_type(name: str)` - No public docstring in the audited version.
- **method**, line 477: `MacSdkRuntime.reflection_type(name: str) -> _Type` - No public docstring in the audited version.
- **method**, line 489: `MacSdkRuntime.resolve_argument(value: Any, aliases: dict[str, Any], *, unsafe: bool)` - No public docstring in the audited version.
- **class**, line 324: `ReactionData` - No public docstring in the audited version.
- **method**, line 376: `ReactionData.Formula() -> str` - No public docstring in the audited version.
- **method**, line 331: `ReactionData.LoadData(data: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 354: `ReactionData.LoadFile(path: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **property**, line 373: `ReactionData.Products` - No public docstring in the audited version.
- **property**, line 369: `ReactionData.Reactants` - No public docstring in the audited version.
- **method**, line 379: `ReactionData.WriteData(mimetype: str = 'chemical/x-mdl-rxn') -> str` - No public docstring in the audited version.
- **method**, line 386: `ReactionData.WriteFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.
- **class**, line 161: `StructureData` - No public docstring in the audited version.
- **method**, line 315: `StructureData.AtomByAtomSearch(target: 'StructureData')` - No public docstring in the audited version.
- **property**, line 263: `StructureData.Atoms` - No public docstring in the audited version.
- **property**, line 267: `StructureData.Bonds` - No public docstring in the audited version.
- **method**, line 259: `StructureData.ChemicalName() -> str` - No public docstring in the audited version.
- **method**, line 292: `StructureData.CleanupStructure() -> bool` - No public docstring in the audited version.
- **method**, line 311: `StructureData.ContainsSubstructure(query: 'StructureData') -> bool` - No public docstring in the audited version.
- **property**, line 243: `StructureData.ElementalAnalysis` - No public docstring in the audited version.
- **property**, line 239: `StructureData.ExactMass` - No public docstring in the audited version.
- **method**, line 231: `StructureData.Formula() -> str` - No public docstring in the audited version.
- **property**, line 247: `StructureData.Inchi` - No public docstring in the audited version.
- **method**, line 177: `StructureData.LoadData(data: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 189: `StructureData.LoadFile(path: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 215: `StructureData.MimeTypes()` - No public docstring in the audited version.
- **method**, line 302: `StructureData.Overlay(target: 'StructureData') -> bool` - No public docstring in the audited version.
- **method**, line 193: `StructureData.ReadFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.
- **property**, line 251: `StructureData.TotalCharge` - No public docstring in the audited version.
- **property**, line 235: `StructureData.Weight` - No public docstring in the audited version.
- **method**, line 271: `StructureData.WriteData(mimetype: str = 'text/xml') -> str` - No public docstring in the audited version.
- **method**, line 278: `StructureData.WriteFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.

## `mcp_runtime.chemscript_sdk_runtime`

- **function**, line 447: `catalog_sdk(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 147: `ChemScriptRuntime` - One direct Python.NET session for cataloging and executing an SDK program.
- **method**, line 289: `ChemScriptRuntime.member_is_interop(reflection_type, member: str) -> bool` - No public docstring in the audited version.
- **method**, line 201: `ChemScriptRuntime.python_type(name: str)` - No public docstring in the audited version.
- **method**, line 187: `ChemScriptRuntime.reflection_type(name: str)` - No public docstring in the audited version.
- **method**, line 224: `ChemScriptRuntime.resolve_argument(value: Any, aliases: dict[str, Any], *, unsafe: bool)` - No public docstring in the audited version.
- **method**, line 213: `ChemScriptRuntime.system_python_type(name: str)` - No public docstring in the audited version.
- **function**, line 603: `execute_program(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 63: `validate_program(program: list[dict[str, Any]], *, allow_file_io: bool = True, allow_unsafe_interop: bool = False) -> list[dict[str, Any]]` - Validate the declarative SDK program without loading Python.NET.

## `mcp_runtime.com_call`

- **function**, line 476: `chemdraw_com_call(program: list[dict[str, Any]], allow_file_io: bool = False, allow_overwrite: bool = False, max_items: int = 100) -> dict[str, Any]` - Run a declarative program over ChemDraw's COM automation objects (Windows, ChemDraw installed).
- **class**, line 66: `ComCallError` - A ChemDraw failure with a stable public code.
- **function**, line 366: `execute_program(application: Any, steps: list[dict[str, Any]], *, max_items: int = 100, allow_overwrite: bool = False, created: Optional[list[Any]] = None, application_launched: bool = False) -> dict[str, Any]` - Run validated steps against ``application``; returns results and written files.
- **class**, line 75: `HandleNotOwnedError` - A write or destructive call on an object the program did not create itself.
- **function**, line 181: `validate_program(program: list[dict[str, Any]], *, allow_file_io: bool = False, allow_overwrite: bool = False) -> list[dict[str, Any]]` - Check the program against the COM catalog and return the steps with their types.

## `mcp_runtime.decimer_api`

- **function**, line 75: `build_multipart_body(*, filename: str, mime_type: str, image_bytes: bytes, hand_drawn: bool, boundary: str | None = None) -> tuple[str, bytes]` - Encode the multipart fields declared by the live OpenAPI document.
- **class**, line 36: `DecimerAPIError` - Raised when the remote DECIMER service cannot return usable SMILES.
- **method**, line 43: `DecimerAPIError.as_result() -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 50: `DecimerUploadRefused` - Raised when upload consent is absent or does not match the prepared upload.
- **function**, line 54: `normalize_api_payload(payload: Any) -> dict[str, Any]` - Normalize both the documented string and live list response shapes.
- **function**, line 471: `recognize_image(image_path: str, *, hand_drawn: bool = False, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS, output_path: str | None = None, confirm_upload: bool = False, approved_sha256: str | None = None, approved_origin: str | None = None) -> dict[str, Any]` - Upload one image to DECIMER and return normalized, validated predictions.
- **function**, line 239: `urlopen(request: Request, *, timeout: int)` - Open a request with redirect checks applied before a redirected upload.

## `mcp_runtime.engine_tools`

- **function**, line 180: `compare_nmr_shifts(smiles: str, experimental_1h: Optional[list[float]] = None, experimental_13c: Optional[list[float]] = None, predicted_result: Optional[dict[str, Any]] = None, solvent: str = 'CDCl3', engines: str = '', outlier_threshold_1h: float = 0.5, outlier_threshold_13c: float = 5.0) -> dict[str, Any]` - Compare experimental 1H and/or 13C NMR shifts against predicted or topological groups for `smiles`.
- **function**, line 114: `extract_structures_from_document(path: str, out_dir: str, pages: Optional[list[int]] = None, engines: str = 'molscribe,molvec', segmenter: str = 'auto', dpi: int = 200, confirm_upload: bool = False, hand_drawn: bool = False) -> dict[str, Any]` - Find every structure on a PDF (pages are 1-based, up to 50) or an image, read each with several engines.
- **function**, line 12: `list_engines() -> dict[str, Any]` - List the optional OCSR, segmentation, reaction, retrosynthesis, condition and NMR engines and which are installed.
- **function**, line 96: `predict_conditions(reactants: str, products: str, engine: Optional[str] = None, count: int = 5, timeout_seconds: int = 900) -> dict[str, Any]` - Rank catalyst, solvent and reagent combinations for a reaction (reactants and products as SMILES).
- **function**, line 135: `predict_nmr(smiles: str, nucleus: str = '1H', solvent: str = 'chloroform', frequency_mhz: float = 400.0, engine: Optional[str] = None, output_path: Optional[str] = None, timeout_seconds: int = 900, experimental_1h: Optional[list[float]] = None, experimental_13c: Optional[list[float]] = None) -> dict[str, Any]` - Predict 1H and/or 13C chemical shifts (`nucleus` "1H", "13C" or "both") of one molecule in a solvent.
- **function**, line 50: `predict_products(reactants: str, reagents: Optional[str] = None, engine: Optional[str] = None, count: int = 5, timeout_seconds: int = 600) -> dict[str, Any]` - Predict likely products of a reaction from reactant SMILES (dot-separated) with a learned model.
- **function**, line 66: `predict_retrosynthesis(product: str, engine: Optional[str] = None, steps: str = 'single', count: int = 5, time_limit: int = 60, timeout_seconds: int = 900, output_cdxml: str = '') -> dict[str, Any]` - Suggest precursors (steps="single") or full routes to purchasable stock (steps="multi") for a target.
- **function**, line 24: `recognize_structure(image_path: str, engines: str = 'decimer-api', hand_drawn: bool = False, output_path: Optional[str] = None, timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: Optional[str] = None, approved_origin: Optional[str] = None) -> dict[str, Any]` - Read one structure image with one or several OCSR engines and compare the answers.

## `mcp_runtime.extended_tools`

- **function**, line 1161: `analyze_lcms_series(files: list[str], output_path: Optional[str] = None, rt_tolerance: float = 0.02, mz_tolerance: float = 0.5, trend_threshold: float = 0.2, ignore_instrument: bool = False, internal_standard_mw: Optional[float] = None, internal_standard_rt: Optional[float] = None, internal_standard_name: str = 'IS') -> dict[str, Any]` - Analyze a time series of standard LCMS data (PDF, .rpt, .daml, report.txt, mzML/mzXML or Waters .raw).
- **function**, line 1254: `assemble_lab_book(input_dir: str, experiment: Optional[str] = None, tracking_json: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Assemble a deterministic lab-book entry from experiment files.
- **function**, line 820: `batch_embed_cdxml_in_office(cdxml_paths: list[str], output_path: str, margin_pt: float = 0) -> dict[str, Any]` - Create PPTX or DOCX containing editable ChemDraw OLE objects.
- **function**, line 472: `clean_scheme_layout(input_path: str, output_path: Optional[str] = None, approach: str = 'chemdraw_mimic', render_preview: bool = True) -> dict[str, Any]` - Clean an existing CDXML reaction layout without changing the source file.
- **function**, line 1119: `discover_experiment_files(input_dir: str, experiment: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Discover and classify files belonging to one experiment.
- **function**, line 744: `fill_office_template(template_path: str, manifest_path: str, output_path: Optional[str] = None) -> dict[str, Any]` - Fill PPTX/DOCX text and editable ChemDraw placeholders from a manifest.
- **function**, line 880: `inspect_chemdraw_objects_in_office(input_path: str, output_dir: Optional[str] = None, render_previews: bool = True) -> dict[str, Any]` - Inventory editable ChemDraw objects and extract numbered CDXML previews.
- **function**, line 518: `merge_reaction_schemes(input_paths: list[str], output_path: Optional[str] = None, mode: str = 'auto', equiv_mode: str = 'default', reference_cdxml: Optional[str] = None, allow_adjacent: bool = True, render_preview: bool = True, force_sequential: bool = False) -> dict[str, Any]` - Merge parallel, sequential, or unrelated CDXML reaction schemes.
- **function**, line 1307: `parse_scifinder_rdf(input_path: str, resolve_cas: bool = False, output_path: Optional[str] = None, confirm_pubchem: bool = False) -> dict[str, Any]` - Parse SciFinder RDF and optionally enrich CAS data over the network.
- **function**, line 605: `polish_reaction_scheme(input_path: str, output_path: Optional[str] = None, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', eln_csv: Optional[str] = None, reference_cdxml: Optional[str] = None, render_preview: bool = True) -> dict[str, Any]` - Run the audited deterministic polishing pipeline on a CDXML scheme.
- **function**, line 637: `render_cdxml_files(input_paths: list[str], output_dir: Optional[str] = None, format: str = 'png', dpi: int = 300) -> dict[str, Any]` - Render one or more CDXML files through native ChemDraw (COM or macOS).
- **function**, line 986: `replace_chemdraw_objects_in_office(input_path: str, replacements_manifest: str, output_path: Optional[str] = None, render_pdf_preview: bool = False, resize_frames: bool = False) -> dict[str, Any]` - Replace selected ChemDraw OLE contents and previews without moving them.
- **function**, line 1415: `segment_large_scheme(cdxml_path: str, output_path: Optional[str] = None, verbose: bool = False) -> dict[str, Any]` - Segment a disconnected or multi-panel CDXML scheme into logical regions.

## `mcp_runtime.figure_draw`

- **function**, line 720: `bold_arrows(cdxml: Any, slug: str) -> Any` - Arrows at 1.5 times the document's line width (the preset's unless a house style measured it).
- **function**, line 732: `bold_compound_numbers(cdxml: Any, grounded: list[dict], house: HouseStyle | None) -> tuple[Any, list[str]]` - Compound numbers in bold, as the journal style sheets set them.
- **function**, line 686: `brief_house(brief: dict) -> HouseStyle | None` - The brief's house style, or None when ``style`` is a measurement preset or absent.
- **function**, line 694: `brief_style(brief: dict) -> tuple[str, float]` - The brief's preset slug (a house style's base preset) and the factor from ACS geometry to it.
- **function**, line 896: `draw_figure(brief: dict | str, output_path: str | None = None, render: bool = False) -> dict` - Draw a reaction scheme from a brief and check it, in one call.
- **function**, line 142: `offline_structure(name: str) -> str | None` - The SMILES a chemical name resolves to offline with normal confidence, else None.
- **function**, line 675: `style_preset_error(style: Any) -> str | None` - Error text for a brief ``style`` that is neither a built-in preset nor a house style, else None.
- **function**, line 710: `style_report(slug: str, house: HouseStyle | None = None, applied: list[str] | None = None, skipped: list[str] | None = None) -> dict` - No public docstring in the audited version.
- **function**, line 701: `styled(cdxml: Any, slug: str) -> Any` - Apply a preset to a document laid out at ACS geometry; ACS documents are unchanged.

## `mcp_runtime.figure_editing`

- **function**, line 4: `apply_crossings(page, crossings)` - No public docstring in the audited version.
- **function**, line 50: `edit_bond_display(node, edit)` - No public docstring in the audited version.

## `mcp_runtime.figure_house`

- **function**, line 79: `add_highlight_fills(brief: dict, grounded: list[dict], house: HouseStyle | None) -> str | None` - Ask the ring_fills decoration for the largest ring of each final product.
- **function**, line 771: `apply_captions_and_title(cdxml: Any, brief: Mapping, grounded: list[dict]) -> tuple[Any, list[str], list[str]]` - Captions under species, then the panel label and title above the whole figure.
- **function**, line 268: `apply_figure_type_conventions(cdxml: Any, house: HouseStyle, figure_type: str, slug: str) -> tuple[Any, list[str], list[str]]` - Apply a card's ``figure_types`` section to a styled drawing; (cdxml, applied, skipped).
- **function**, line 319: `apply_house_conventions(cdxml: Any, brief: Mapping, grounded: list[dict], house: HouseStyle) -> tuple[Any, list[str], list[str], list[str]]` - Edit the drawn scheme; returns (cdxml, applied, skipped reasons, warnings).
- **function**, line 213: `apply_measured_geometry(cdxml: Any, house: HouseStyle, slug: str) -> tuple[Any, list[str], list[str]]` - Line width, bold width and atom-label size from the card's ``measured`` ratios.
- **function**, line 859: `apply_scope_conventions(cdxml: Any, brief: Mapping, grounded: list[dict], house: HouseStyle | None, slug: str) -> tuple[Any, list[str], list[str], list[str]]` - A scope page already in its preset: compound-number face and colour, the brief's species colours and abbreviations (the card's abbreviate_groups too), then the measured geometry.
- **function**, line 812: `apply_species_boxes(cdxml: Any, brief: Mapping, grounded: list[dict]) -> tuple[Any, list[str]]` - A frame (solid, dashed or rounded) and/or a fill behind each species that asks for one.
- **function**, line 584: `apply_species_styling(cdxml: Any, brief: Mapping, grounded: list[dict], house: HouseStyle | None = None) -> tuple[Any, list[str], list[str]]` - The brief's own colours, abbreviations and condition-text runs; returns (cdxml, applied, warnings).
- **function**, line 505: `condition_line_errors(line: Any, where: str) -> list[str]` - A condition line is text, a run {text, color?, bold?, italic?} or a list of runs.
- **function**, line 524: `condition_text(line: Any) -> str` - The plain text of a condition line.
- **function**, line 66: `final_products(brief: Mapping) -> list[str]` - No public docstring in the audited version.
- **function**, line 37: `format_yield(text: str, template: str | None) -> str` - ``template`` filled with the number of a yield such as "85%"; other text is kept.
- **function**, line 205: `measured_arrow_bonds(house: HouseStyle | None) -> float | None` - The shortest arrow in bond lengths from the card's measurements, or None.
- **function**, line 692: `panel_errors(brief: Mapping) -> list[str]` - Problems with the title, panel label, captions and boxes of a brief.
- **function**, line 470: `species_style_errors(entry: Mapping) -> list[str]` - Problems with a species' colour and abbreviation keys, for the brief check.
- **function**, line 57: `split_conditions(above: list[str], below: list[str], house: HouseStyle | None) -> tuple[list, list]` - No public docstring in the audited version.
- **function**, line 45: `step_yield(step: Mapping, house: HouseStyle | None) -> str | None` - The yield text drawn under the arrow, or None when the house style moves it.

## `mcp_runtime.figure_lint`

- **function**, line 376: `lint_cdxml(cdxml_text: str, max_width: Optional[float] = None) -> List[Dict[str, Any]]` - Return a list of issues; an empty list means the geometry checks passed.

## `mcp_runtime.figure_mechanism`

- **function**, line 645: `draw_mechanism(brief: dict, output_path: str | None, render: bool) -> dict` - Draw a mechanism; called by draw_figure for ``kind: mechanism``.

## `mcp_runtime.figure_molecule`

- **function**, line 497: `draw_molecule_figure(brief: dict, output_path: str | None, render: bool) -> dict` - Draw one molecule or a grid of structures; called by draw_figure for ``kind: molecule``.

## `mcp_runtime.figure_scope`

- **function**, line 175: `draw_scope(brief: dict, output_path: str | None, render: bool) -> dict` - Draw a scope panel; called by draw_figure for ``kind: scope``.

## `mcp_runtime.figure_tools`

- **function**, line 1471: `compare_figure_images(reference_path: str, candidate_path: str, output_path: str) -> dict` - Compare aligned local raster previews without resizing or warping.
- **function**, line 611: `compose_chemical_figure(manifest_path: str, output_path: str) -> dict` - Compose editable CDXML using explicit point coordinates and grounded molecules.
- **function**, line 165: `rdkit_workbench(molecules: list[dict] | str | None = None, operation: str = 'inspect', options: dict | None = None, output_path: str | None = None, **kwargs) -> dict` - Analyze and edit grounded molecules: inspect, stereoisomers, tautomers, mcs, r_groups, set_stereo, edit_structure, edit_smarts, read_wedges, depict_like, enumerate_markush.

## `mcp_runtime.figure_validation`

- **function**, line 76: `compare_inventories(a, b)` - No public docstring in the audited version.
- **function**, line 43: `inspect_document(path)` - No public docstring in the audited version.
- **function**, line 105: `validate_figure(input_path: str, output_dir: str, native: bool = False, cross_reader: bool = False, session = None, render_png: bool = False) -> dict` - Write a diagnostic directory without changing the source. CLI-only operation.
- **function**, line 160: `validate_figures(input_paths, output_dir: str, native: bool = False, cross_reader: bool = False, session = None, render_png: bool = False) -> dict` - Validate multiple CDXML figures in a batch reusing a shared NativeRenderSession.

## `mcp_runtime.generate_reference`

- **function**, line 32: `manifest(profile: str = 'full') -> dict` - No public docstring in the audited version.
- **function**, line 57: `render_markdown(profile: str = 'full') -> str` - No public docstring in the audited version.
- **function**, line 92: `render_reference(profile: str = 'full') -> str` - Signature reference used by the Skill's catalog checks.

## `mcp_runtime.install_decimer_models`

- **function**, line 48: `download(url: str, destination: Path, proxy: str | None) -> None` - No public docstring in the audited version.
- **function**, line 58: `file_hash(path: Path, algorithm: str) -> str` - No public docstring in the audited version.
- **function**, line 129: `install_model(model: dict[str, str], target: Path, *, proxy: str | None, downloader = download) -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 66: `md5(path: Path) -> str` - No public docstring in the audited version.
- **function**, line 74: `safe_extract(archive: Path, destination: Path) -> None` - No public docstring in the audited version.
- **function**, line 87: `select_models(keys: list[str] | None) -> list[dict[str, str]]` - No public docstring in the audited version.
- **function**, line 70: `sha256(path: Path) -> str` - No public docstring in the audited version.

## `mcp_runtime.live_chemdraw`

- **function**, line 392: `live_chemdraw_session(action: str = 'status', *, cdxml: str = '', smiles: str = '', output_path: str = '') -> dict[str, Any]` - Interact non-destructively with an already-open user-facing desktop ChemDraw window.

## `mcp_runtime.markush_tools`

- **function**, line 30: `markush_compile(spec_path: str, output_dir: str, layout_path: str | None = None, render: bool = True) -> dict` - Compile a spec into markush.cxsmiles, markush.mol (V3000), markush.cdxml and a native PNG.
- **function**, line 83: `markush_detect(image_path: str, output_dir: str) -> dict` - Find text boxes, bonds and ring circles in a clean Markush drawing.
- **function**, line 62: `markush_enumerate(spec_path: str, count: int = 5, seed: int = 0) -> dict` - Sample concrete members from the definition values of a spec (SMILES).
- **function**, line 23: `markush_validate(spec_path: str) -> dict` - Check a markush.json spec; every error says what to change.

## `mcp_runtime.mcp_compat`

- **function**, line 46: `install_legacy_fastmcp_alias() -> None` - Provide the legacy FastMCP import expected by the core MCP module.
- **function**, line 20: `sdk_major(version: str | None = None) -> int` - Return a supported MCP SDK major version or raise a clear error.
- **function**, line 13: `sdk_version() -> str` - Return the installed MCP Python SDK distribution version.
- **function**, line 35: `server_class() -> type[Any]` - Return the high-level server class for the installed SDK.

## `mcp_runtime.mcp_server`

- **class**, line 671: `ApiKeyMiddleware` - Require a bearer token without placing it in logs or worker environments.
- **function**, line 1170: `build_http_app(args: argparse.Namespace, *, environ = None)` - No public docstring in the audited version.
- **function**, line 1099: `build_server(*, profile: str | None = None, **server_settings)` - No public docstring in the audited version.
- **function**, line 1062: `list_registered_resources_and_prompts(mcp: typing.Any = None) -> dict[str, typing.Any]` - Return the MCP resource URI templates and prompt names registered on the server.
- **function**, line 1138: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` - No public docstring in the audited version.
- **function**, line 892: `read_reference_resource(slug: str) -> str` - No public docstring in the audited version.
- **function**, line 929: `read_style_guide_resource(preset: str) -> str` - JSON settings of one preset or house-style card, or of all of them for ``all``.
- **function**, line 906: `read_template_resource(slug: str) -> str` - No public docstring in the audited version.
- **function**, line 735: `resolve_http_configuration(*, host: str, port: int, allowed_hosts: list[str], allowed_origins: list[str], environ: typing.Mapping[str, str] | None = None, api_key_env: str = 'CHEMDRAW_MCP_HTTP_API_KEY') -> dict[str, typing.Any]` - Validate remote HTTP exposure and return non-secret server settings.
- **function**, line 1208: `run_streamable_http(args: argparse.Namespace) -> None` - No public docstring in the audited version.

## `mcp_runtime.metal_templates`

- **function**, line 225: `apply_hapto_templates(cdxml: str, templates: dict[str, MetalTemplate]) -> str` - Replace each drawn fragment whose structure is an eta-n template by the template drawing.
- **function**, line 97: `find_template(name: str | None = None, smiles: str | None = None) -> MetalTemplate | None` - The template a species name or SMILES describes, else None.
- **function**, line 111: `fragment_graph(fragment: ET.Element) -> Chem.Mol` - The drawn connectivity of a fragment, eta-n attachments counted as bonds to every ring atom.
- **function**, line 179: `hapto_fragment(template: MetalTemplate, center_x: float, center_y: float, first_id: int) -> ET.Element` - A CDXML fragment of an eta-n template centred on the given point, ids from ``first_id``.
- **class**, line 35: `MetalTemplate` - No public docstring in the audited version.
- **function**, line 210: `strip_hapto(fragment: ET.Element) -> ET.Element` - A copy of a fragment without its multi-attachment nodes and their bonds (for structure read-back).

## `mcp_runtime.native_io`

- **function**, line 153: `ascii_input_directory(source: str | Path, *, suffixes: Sequence[str] = ('.cdxml', '.cdx', '.csv', '.rxn')) -> Iterator[tuple[Path, dict[str, str]]]` - No public docstring in the audited version.
- **function**, line 136: `ascii_inputs(sources: Sequence[str | Path]) -> Iterator[list[Path]]` - No public docstring in the audited version.
- **function**, line 119: `ascii_workspace(prefix: str = 'cdx-') -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 387: `batch_convert_cdxml(sources: Sequence[str | Path], batch_convert: Callable[[list[str]], Any]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 257: `bridge_file(source: str | Path, destination: str | Path, operation: Callable[[Path, Path], Any], *, output_kind: str | None = None, preserve_source_context: bool = False) -> Any` - No public docstring in the audited version.
- **function**, line 416: `convert_cdx_bytes_to_cdxml(cdx_data: bytes, converter: Callable[..., Any]) -> str` - No public docstring in the audited version.
- **class**, line 20: `NativeIOError` - Native automation failure with a stable public error code.
- **function**, line 33: `normalize_cdxml_staging(path: Path) -> None` - Normalize a staged copy for native use; the source document is never changed.
- **function**, line 479: `rewrite_json_paths(path: str | Path, replacements: dict[str, str]) -> None` - No public docstring in the audited version.
- **function**, line 180: `validate_native_output(path: str | Path, kind: str | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 437: `write_shadow_manifest(manifest: str | Path, workspace: str | Path) -> tuple[Path, list[Path]]` - No public docstring in the audited version.

## `mcp_runtime.native_renderer`

- **function**, line 83: `acquire_application()` - ``(application, launched)`` from the one shared acquisition path (a private instance).
- **class**, line 37: `NativeRenderError` - ChemDraw rendering failure with a stable public error code.
- **class**, line 132: `NativeRenderSession` - Lazily acquire and reuse one ChemDraw application for native exports.
- **method**, line 175: `NativeRenderSession.com_application()` - The session's private, hidden ChemDraw COM application (Windows only).
- **method**, line 222: `NativeRenderSession.render(source: str | Path, destination: str | Path, dpi: int = 300) -> str` - No public docstring in the audited version.
- **function**, line 293: `render_cdxml(source: str | Path, destination: str | Path, *, dpi: int = 300, timeout_seconds: int = 30) -> str` - No public docstring in the audited version.
- **function**, line 32: `renderer_name() -> str` - The native renderer on this platform, as written in render receipts.

## `mcp_runtime.object_tools`

- **function**, line 228: `chemdraw_inventory(layer: str | None = None, query: str | None = None, tier: str | None = None, kind: str | None = None, limit: int = 50) -> dict` - Look up ChemDraw's own interfaces and how far this Skill covers each one.
- **function**, line 75: `chemdraw_object(op: str, input_path: str, selector: str | None = None, tag: str | None = None, props: dict | None = None, children: list | None = None, text: str | None = None, output_path: str | None = None, allow_unknown: bool = False, dry_run: bool = False, verify: bool = True, limit: int = 200) -> dict` - List, read, change, add or delete any object in a CDXML file, without touching the input.

## `mcp_runtime.office_objects`

- **function**, line 31: `com_apartment()` - Initialize COM for the current worker thread and release it symmetrically.
- **function**, line 602: `emf_frame_size(data: bytes) -> tuple[int, int] | None` - Width and height of an EMF picture frame in 0.01 mm, or None if not an EMF.
- **function**, line 531: `load_replacement_manifest(manifest_path: str | Path, *, source_sha256: str, objects: list[dict[str, Any]]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 787: `render_office_pdf(office_path: str | Path, output_path: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 638: `resize_ole_frame(xml: bytes, relationship_id: str, scale_x: float, scale_y: float) -> bytes` - Scale the frame of the OLE object ``relationship_id`` in a slide or document part.
- **function**, line 679: `rewrite_office_package(input_path: str | Path, output_path: str | Path, replacement_parts: dict[str, dict[str, bytes]]) -> None` - Write a copy of an Office package with replaced OLE objects and previews.
- **function**, line 289: `scan_office_objects(input_path: str | Path) -> tuple[str, list[dict[str, Any]]]` - No public docstring in the audited version.
- **function**, line 56: `sha256_file(path: str | Path) -> str` - No public docstring in the audited version.
- **function**, line 809: `validate_pdf(path: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 445: `write_inspection(input_path: str | Path, output_dir: str | Path, *, render_previews: bool) -> dict[str, Any]` - No public docstring in the audited version.

## `mcp_runtime.official_overrides`

- **function**, line 234: `convert_cdx_cdxml(input_path: str, output_path: Optional[str] = None) -> dict` - Convert CDX/CDXML through a validated no-overwrite staging file.
- **function**, line 74: `draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict` - Draw a molecule through a validated no-overwrite staging file.
- **function**, line 408: `embed_cdxml_in_office(cdxml_path: str, office_path: str, output_path: str | None = None) -> dict` - Create a new validated PPTX or DOCX and reject all existing targets.
- **function**, line 299: `extract_cdxml_from_office(file_path: str, output_dir: Optional[str] = None) -> dict` - Extract every object transactionally; publish nothing on partial failure.
- **function**, line 281: `format_lab_entry(entries_json: Union[list[dict], dict, str], output_path: Optional[str] = None) -> dict` - Format a lab entry and atomically publish verified text.
- **function**, line 263: `parse_analysis_file(pdf_path: str, output_path: Optional[str] = None) -> dict` - Parse an analysis file and atomically publish verified JSON.
- **function**, line 142: `parse_reaction(cdxml: Optional[str] = None, cdx: Optional[str] = None, csv: Optional[str] = None, rxn: Optional[str] = None, input_dir: Optional[str] = None, output_path: Optional[str] = None) -> dict` - Parse a reaction and atomically publish its JSON descriptor.
- **function**, line 219: `parse_scheme(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Parse a scheme and atomically publish its JSON descriptor.
- **function**, line 108: `render_scheme(yaml_text: Optional[str] = None, compact_text: Optional[str] = None, json_path: Optional[str] = None, layout: str = 'auto', output_path: Optional[str] = None) -> str` - Render a scheme (yaml_text, compact_text with @layout/-->/..>/X>/run[1], or json_path) through a validated no-overwrite staging file.
- **function**, line 453: `render_to_png(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Render CDXML to a validated PNG through a staging file.

## `mcp_runtime.process_control`

- **function**, line 295: `cleanup_automation_processes(before: dict[int, dict[str, Any]], after: dict[int, dict[str, Any]], *, stage_pid: int, terminate: bool = True, deadline: float | None = None) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 119: `pid_is_running(pid: int) -> bool` - No public docstring in the audited version.
- **function**, line 216: `snapshot_automation_processes(timeout_seconds: float = 5) -> dict[int, dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 92: `terminate_pid(pid: int, timeout_seconds: float = 10) -> bool` - No public docstring in the audited version.

## `mcp_runtime.publication_figure`

- **function**, line 32: `publication_figure(operation: str, spec_path: str, output_dir: str) -> dict` - Create, update, or check editable substrate-scope and SAR figure projects.

## `mcp_runtime.remote_tools`

- **function**, line 10: `extract_structures_via_decimer_api(image_path: str, hand_drawn: bool = False, output_path: Optional[str] = None, timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: Optional[str] = None, approved_origin: Optional[str] = None) -> dict[str, Any]` - Default image-recognition tool: use the remote DECIMER API.

## `mcp_runtime.report_tools`

- **function**, line 1609: `characterization_text(compounds: list[dict], options: dict | None = None, output_path: str | None = None) -> dict` - ACS-style characterization paragraph per compound, in the order of the ACS Style Guide.
- **function**, line 592: `check_reaction_balance(reaction: str | dict, options: dict | None = None, output_path: str | None = None) -> dict` - Check that a reaction conserves atoms and charge, and optionally tabulate its stoichiometry.
- **function**, line 879: `chemdraw_chemical_properties(molecules: list[dict], output_path: str | None = None) -> dict` - Formula, masses, elemental analysis, logP and molar refractivity as ChemDraw computes them.
- **function**, line 656: `export_structures(source: str | list, options: dict | None = None, output_path: str | None = None) -> dict` - Export every structure in a file or list as SMILES, InChI, InChIKey, formula and mass.
- **function**, line 1022: `hrms_line(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict` - HRMS characterization lines: "HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0570".
- **function**, line 1525: `map_reaction_atoms(reaction: str | dict | list, options: dict | None = None, output_path: str | None = None) -> dict` - Map each product atom to the reactant atom it comes from (atom-to-atom mapping).
- **function**, line 291: `molecule_report(molecules: list[dict], output_path: str | None = None) -> dict` - Property sheet for grounded molecules: formula, masses, MS adducts, drug-likeness.
- **function**, line 1305: `route_summary(steps: list, options: dict | None = None, output_path: str | None = None) -> dict` - Overall yield and cumulative process mass intensity (PMI) of a synthetic route.
- **function**, line 1169: `si_materials_tables(reactions: list, options: dict | None = None, output_path: str | None = None) -> dict` - Materials tables for a batch of reactions, ready for a Supporting Information file.
- **function**, line 447: `signs(species)` - No public docstring in the audited version.
- **function**, line 987: `stoichiometry_grid(source: str, mode: str = 'analyze', output_path: str | None = None, options: dict | None = None) -> dict` - ChemDraw's own stoichiometry grid (Structure > Analyze Stoichiometry), drawn or read back.
- **function**, line 749: `structure_to_name(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict` - Name grounded structures with ChemDraw's own structure-to-name engine and check each name.

## `mcp_runtime.resource_lock`

- **function**, line 46: `native_resource_lock(resource_class: str | None, timeout_seconds: int) -> Iterator[None]` - Serialize ChemDraw automation across workers in the current user session.
- **class**, line 34: `ResourceBusyError` - Raised when an exclusive native resource cannot be acquired in time.

## `mcp_runtime.runtime_diagnostics`

- **function**, line 704: `diagnose_runtime(run_native_probe: bool = False, run_office_probe: bool = False, run_chemscript_probe: bool = False) -> dict[str, Any]` - Report local runtime capabilities; native probes are explicit and temporary.

## `mcp_runtime.runtime_discovery`

- **class**, line 23: `Discovery` - No public docstring in the audited version.
- **method**, line 27: `Discovery.to_dict() -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 284: `find_chemdraw(explicit: str | None = None) -> Discovery` - Find ChemDraw from explicit, environment, the macOS application, COM, then common paths.
- **function**, line 139: `find_python(explicit: str | None = None) -> Discovery` - Find and probe Python using explicit, environment, then implicit paths.
- **function**, line 180: `find_skill_root(explicit: str | None = None) -> Discovery` - No public docstring in the audited version.

## `mcp_runtime.scientific_tool`

- **function**, line 23: `scientific_workflow(operation: str, spec_path: str, output_path: str) -> dict[str, Any]` - Draw or analyse a scientific figure from a JSON spec file: tlc, apparatus, mechanism, nmr or plot.

## `mcp_runtime.structure_fidelity`

- **function**, line 219: `repair_and_validate_drawn_cdxml(smiles: str, path: str | Path, *, repair_stereo: bool = True) -> dict[str, object]` - Repair missing wedge bonds and verify CDXML against the source SMILES.
- **class**, line 9: `StructureFidelityError` - Generated CDXML does not preserve the requested molecular structure.

## `mcp_runtime.telemetry`

- **function**, line 38: `configure_tools(names: Iterable[str]) -> None` - Set the finite tool-label vocabulary used by exported metrics.
- **function**, line 106: `health_snapshot(*, tool_count: int) -> dict` - Return process health without input, output, filename, or molecule data.
- **function**, line 100: `native_active_finished() -> None` - No public docstring in the audited version.
- **function**, line 94: `native_active_started() -> None` - No public docstring in the audited version.
- **function**, line 88: `native_wait_finished() -> None` - No public docstring in the audited version.
- **function**, line 82: `native_wait_started() -> None` - No public docstring in the audited version.
- **function**, line 136: `render_prometheus() -> str` - Render the current process metrics using the Prometheus text format.
- **function**, line 217: `reset_for_tests() -> None` - No public docstring in the audited version.
- **function**, line 56: `worker_finished(tool: str, *, duration_seconds: float, ok: bool, error_code: str | None) -> None` - No public docstring in the audited version.
- **function**, line 49: `worker_started(tool: str) -> None` - No public docstring in the audited version.

## `mcp_runtime.temp_compat`

- **function**, line 47: `ensure_usable_mkdtemp(is_usable: Optional[Callable[[], bool]] = None) -> bool` - Replace ``tempfile.mkdtemp`` when its folders are unusable. Returns True when it was replaced.
- **function**, line 19: `mkdtemp_is_usable() -> bool` - Whether a folder made by ``tempfile.mkdtemp`` accepts a file.

## `mcp_runtime.tool_registry`

- **function**, line 38: `build_acs_figure(spec: dict[str, Any] | str, output_path: str | None = None, render: bool = False) -> dict[str, Any]` - Build an ACS Document 1996 CDXML figure from an acs_builder JSON spec.
- **function**, line 376: `build_registry(profile: str | None = None) -> dict[str, ToolSpec]` - No public docstring in the audited version.
- **function**, line 418: `load_tool(name: str) -> ToolSpec | None` - One tool's spec, importing only the module that defines it.
- **function**, line 286: `normalize_profile(profile: str | None = None) -> str` - Return the canonical profile name; None means CHEMDRAW_MCP_PROFILE or the default.
- **function**, line 391: `render_manifest() -> str` - The generated tool manifest: where each tool lives and how long it may run.
- **function**, line 409: `tool_manifest() -> dict[str, dict[str, Any]]` - The committed manifest's tool table; empty when the file is missing or unreadable.
- **class**, line 139: `ToolSpec` - No public docstring in the audited version.

## `mcp_runtime.tool_worker`

- **function**, line 174: `common_path_names(fn) -> dict[str, str]` - The common names a caller may use for this tool's file arguments.
- **function**, line 31: `worker_log_dir() -> Path` - Folder of ``worker-<id>.log`` files (``cdx.py doctor --paths`` prints it).

## `mcp_runtime.ui_apps`

- **function**, line 3984: `open_drawing_studio(template: str = 'blank', *, cdxml_path: str | None = None, smiles: str | None = None, name: str | None = None, style: str = 'acs1996', output_path: str | None = None, fragment_path: str | None = None, launch_browser: bool = False) -> dict[str, Any]` - Open the interactive 2D ChemDraw Studio with ring fusion, drag-bond drawing & templates.
- **function**, line 3740: `render_drawing_studio_app_html(initial_payload: dict[str, Any] | None = None, *, live_sync_url: str | None = None) -> str` - Render the standalone / MCP-App HTML document wrapping the 2D Studio fragment.
- **function**, line 1134: `render_drawing_studio_fragment(initial_payload: dict[str, Any] | None = None) -> str` - Render a pure HTML fragment (<div id='cdx-studio-root'>...</div>) with NO document tags.
- **function**, line 343: `render_molstar_app_html(initial_payload: dict[str, Any] | None = None) -> str` - Render the self-contained Mol* + offline 3D WebGL/Canvas MCP App HTML page.
- **function**, line 4124: `serve_drawing_studio(*, template: str = 'blank', cdxml_path: str | None = None, smiles: str | None = None, style: str = 'acs1996', sync_dir: str | Path = '.', port: int = 0, open_browser: bool = True) -> tuple[ThreadingHTTPServer, str, Path]` - Start a local loopback HTTP bridge so terminal CLI agents receive live 2D edits.
- **function**, line 3791: `view_molecule_3d(query: str = 'aspirin', *, structure_path: str | None = None, smiles: str | None = None, pdb_id: str | None = None, format: str | None = None, representation: str = 'ball-and-stick', output_path: str | None = None, launch_browser: bool = False) -> dict[str, Any]` - Build an interactive 3D Mol* + offline WebGL/Canvas viewer (MCP App + standalone HTML).

## `model.document`

- **function**, line 48: `catalog_index() -> dict[str, dict[str, dict[str, Any]]]` - Catalog elements as ``{element: {attribute: {kind, values?}}}``.
- **class**, line 90: `Document` - A parsed CDXML file; ``prologue`` is the text before the root element.
- **method**, line 254: `Document.add(parent: ET.Element, tag: str, props: Optional[dict[str, Any]] = None, *, children: Optional[list[dict[str, Any]]] = None, text: Optional[str] = None, allow_unknown: bool = False) -> ET.Element` - Append a new element (and nested ``children``) to ``parent``; ids are assigned.
- **method**, line 172: `Document.check() -> list[dict[str, Any]]` - Structural problems: duplicate ids and references to objects that do not exist.
- **method**, line 292: `Document.delete(element: ET.Element) -> int` - Remove ``element`` and its subtree; refuse the root and objects other objects point at.
- **method**, line 155: `Document.describe(element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> dict[str, Any]` - No public docstring in the audited version.
- **method**, line 315: `Document.dump_bytes() -> bytes` - No public docstring in the audited version.
- **method**, line 308: `Document.dumps() -> str` - No public docstring in the audited version.
- **method**, line 99: `Document.elements() -> Iterable[ET.Element]` - No public docstring in the audited version.
- **method**, line 109: `Document.ids() -> set[str]` - No public docstring in the audited version.
- **method**, line 250: `Document.next_id() -> int` - No public docstring in the audited version.
- **method**, line 102: `Document.parent_map() -> dict[int, ET.Element]` - ``{id(child): parent}`` for the whole tree; rebuild it after an edit.
- **method**, line 106: `Document.parent_of(element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> Optional[ET.Element]` - No public docstring in the audited version.
- **method**, line 146: `Document.path_of(element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> str` - No public docstring in the audited version.
- **method**, line 112: `Document.select(selector: str) -> list[ET.Element]` - Elements matching ``step > step ...``; a step is ``tag#id[Attr=value]...``.
- **method**, line 226: `Document.set_properties(element: ET.Element, props: dict[str, Any], *, allow_unknown: bool = False) -> dict[str, tuple]` - Set, replace or (with ``None``) remove attributes; returns ``{name: (old, new)}``.
- **function**, line 337: `load(path: str | Path) -> Document` - No public docstring in the audited version.
- **function**, line 319: `parse(source: str | bytes) -> Document` - Parse CDXML text or bytes; the root must be ``CDXML``.

## `postconditions`

- **function**, line 234: `check_cdxml_annotations(cdxml: Union[str, Path]) -> PostconditionResult` - Charges and radicals a reader sees in the drawing agree with the semantic structure.
- **function**, line 65: `check_changed(before: Structure, after: Structure) -> PostconditionResult` - An edit must change the structure; a no-op is not a successful edit.
- **function**, line 127: `check_charge_conserved(before: Structure, after: Structure, *, expected_change: int = 0) -> PostconditionResult` - Net charge of ``after`` equals that of ``before`` plus ``expected_change``.
- **function**, line 145: `check_connected_metal(value: Structure, *, max_ligand_fragments: int = 1) -> PostconditionResult` - Flag an organometallic drawn as a neutral lone metal atom beside several ligand pieces.
- **function**, line 213: `check_formula(expected: Union[str, Mapping[str, int]], value: Structure) -> PostconditionResult` - The formula computed from the input notation equals the formula of the result.
- **function**, line 73: `check_preserved(before: Structure, after: Structure, *, targeted_atoms: Iterable[int] = (), timeout: int = 5) -> PostconditionResult` - Atoms and bonds outside ``targeted_atoms`` (atom indices of ``before``) are unchanged.
- **function**, line 112: `check_stereocentres(value: Structure, *, max_unspecified: int = 0) -> PostconditionResult` - At most ``max_unspecified`` stereocentres may lack a configuration.
- **function**, line 291: `failure_payload(result: PostconditionResult, rejected_result: Any = None, *, hint: str | None = None) -> dict` - Tool-level failure for a failed post-condition, keeping the rejected output for inspection.
- **function**, line 305: `first_failure(*results: PostconditionResult) -> PostconditionResult | None` - The first failed result, or None when every check passed.
- **function**, line 168: `formula_counts(value: Union[str, Mapping[str, int], 'Chem.Mol']) -> Counter` - Element counts (hydrogens included) of a molecule, a mapping, or a plain formula such as ``C4H9Br`` or ``Ca(OH)2``. A SMILES string is not a formula: pass a Mol.
- **function**, line 206: `hill_formula(counts: Mapping[str, int]) -> str` - No public docstring in the audited version.
- **class**, line 29: `PostconditionResult` - Outcome of one check. ``code`` is a stable machine-readable identifier.
- **function**, line 123: `total_charge(value: Structure) -> int` - No public docstring in the audited version.
- **function**, line 105: `unspecified_stereocentres(value: Structure) -> list[int]` - Indices of tetrahedral stereocentres without an assigned configuration.

## `publication.data`

- **function**, line 146: `field_text(record, field)` - No public docstring in the audited version.
- **function**, line 83: `load_records(spec, base)` - No public docstring in the audited version.
- **function**, line 15: `local_path(base, value)` - No public docstring in the audited version.
- **function**, line 11: `sha256(path)` - No public docstring in the audited version.
- **function**, line 36: `table_rows(path, sheet = None)` - No public docstring in the audited version.
- **function**, line 155: `write_json(path, value)` - No public docstring in the audited version.

## `publication.house_styles`

- **function**, line 200: `group_name(name: str) -> str` - The table name of an abbreviation, resolving accepted spellings.
- **function**, line 421: `house_style(name: str, directory: str | Path | None = None) -> HouseStyle` - One house style by slug or display name (any case).
- **function**, line 457: `house_style_summary(style: HouseStyle) -> dict` - The fields ``cdx.py styles`` lists.
- **class**, line 209: `HouseStyle` - No public docstring in the audited version.
- **method**, line 230: `HouseStyle.as_dict() -> dict` - No public docstring in the audited version.
- **method**, line 220: `HouseStyle.convention(key: str, default: Any = None) -> Any` - No public docstring in the audited version.
- **method**, line 224: `HouseStyle.figure_convention(figure_type: str, key: str, default: Any = None) -> Any` - A convention of one figure type (``mechanism``, ``catalytic_cycle`` ...), or ``default``.
- **function**, line 400: `list_house_styles(directory: str | Path | None = None) -> list[HouseStyle]` - No public docstring in the audited version.
- **function**, line 376: `load_house_styles(directory: str | Path | None = None) -> dict[str, HouseStyle]` - Every card in the data folder (or ``directory``), validated, by slug.
- **function**, line 432: `resolve_style(name: str, directory: str | Path | None = None) -> tuple[str, Any]` - ("preset", preset dict) for a measurement preset, ("house", HouseStyle) for a house style.
- **function**, line 240: `validate_card(card: Any, *, source: str = 'card') -> HouseStyle` - A :class:`HouseStyle` from one card; ValueError listing every problem otherwise.

## `publication.layout`

- **function**, line 227: `bounds(node, style)` - No public docstring in the audited version.
- **function**, line 249: `check_pages(project, roots, spec)` - No public docstring in the audited version.
- **function**, line 125: `create_pages(records, spec, stage, start_index = 0)` - No public docstring in the audited version.
- **function**, line 25: `font_for(style, size = None)` - No public docstring in the audited version.
- **function**, line 84: `formula_runs(value, bold = False)` - Text as runs with formula digits subscripted (K2CO3, CH2Cl2), by the shared condition-text rule.
- **function**, line 53: `fragment_mol(fragment)` - No public docstring in the audited version.
- **function**, line 64: `molecule_coordinates(mol, bond_length, reference = None)` - No public docstring in the audited version.
- **function**, line 60: `node_text(node)` - No public docstring in the audited version.
- **function**, line 245: `overlap(a, b)` - No public docstring in the audited version.
- **function**, line 98: `prepare(records, spec)` - No public docstring in the audited version.
- **function**, line 15: `style_settings(spec)` - No public docstring in the audited version.
- **function**, line 36: `text_width(value, style, size = None)` - No public docstring in the audited version.
- **function**, line 41: `wrap(value, width, style)` - No public docstring in the audited version.

## `publication.update`

- **function**, line 38: `match_objects(group, record)` - No public docstring in the audited version.
- **function**, line 17: `matching_group(root, record)` - No public docstring in the audited version.
- **function**, line 57: `replace_text(node, old, new)` - Preserve unchanged rich runs; single-run labels retain all their style.
- **function**, line 87: `replacement_fragment(old_fragment, new_smiles, atom_map, stage, root, cid)` - No public docstring in the audited version.
- **function**, line 152: `update_pages(base_project, base_dir, records, spec, spec_dir, stage)` - No public docstring in the audited version.

## `reaction_calculator.annotate`

- **function**, line 17: `key(mol_or_smiles) -> str | None` - No public docstring in the audited version.
- **function**, line 44: `read_fragments_from_text(text: str)` - (id, mol) of each top-level fragment of CDXML text.

## `reaction_calculator.engine`

- **function**, line 65: `compute(state: dict) -> dict` - Amounts of every row from the limiting row and the quantity fixed on each row.

## `reaction_calculator.hazards`

- **function**, line 423: `assess(smiles: str) -> dict` - Inspect ``smiles`` against the table and structural class alerts.
- **function**, line 411: `class_alerts(smiles: str) -> list[dict]` - Return SMARTS structural hazard class alerts matched by ``smiles``.
- **function**, line 432: `entries() -> list[dict]` - No public docstring in the audited version.
- **function**, line 491: `for_rows(rows: list[dict]) -> list[dict]` - A safety item per reactant, reagent, catalyst and solvent row: the entry, or ``listed: False``.
- **function**, line 470: `incompatibilities(rows: list[dict]) -> list[dict]` - Dangerous combinations among the species of one reaction: ``key``, the two names, warning and source.
- **function**, line 515: `lines(items: list[dict], combinations: list[dict] | tuple = ()) -> list[str]` - Footer lines: the heading, dangerous combinations, one line per listed species, the species not listed.
- **function**, line 376: `lookup(smiles: str) -> dict | None` - The entry for a structure (stereo and drawing coordinates ignored), or None when it is not listed.
- **function**, line 436: `summary(entry: dict) -> str` - One line: signal word, pictograms, statements, boiling and flash point, note.

## `reaction_calculator.library`

- **function**, line 100: `by_name(text: str) -> dict | None` - The library entry for a name or common abbreviation (case-insensitive).
- **function**, line 90: `by_smiles(smiles: str) -> dict | None` - The library entry for a structure, matched on canonical SMILES (stereo and isotopes ignored).
- **function**, line 105: `entries() -> list[dict]` - Every entry once.

## `reaction_calculator.materials`

- **function**, line 127: `csv_text(entries: list[dict]) -> str` - No public docstring in the audited version.
- **function**, line 169: `html_text(entries: list[dict]) -> str` - No public docstring in the audited version.
- **function**, line 110: `markdown(entries: list[dict]) -> str` - No public docstring in the audited version.
- **function**, line 49: `procedure(rows: list[dict], limiting: str, totals: dict) -> str` - One sentence in the usual experimental style, from computed rows.
- **function**, line 20: `trim(value, digits: int = 3) -> str` - Significant digits without trailing zeros: 1.00 -> 1, 94.2 -> 94.2.
- **function**, line 34: `volume_phrase(ml: float) -> str` - No public docstring in the audited version.

## `reaction_calculator.state`

- **function**, line 69: `build_state(sides: dict, options: dict | None = None) -> dict` - Rows for one reaction; ``sides`` maps reactants, agents and products to species dicts.

## `reaction_templates`

- **function**, line 105: `classify(reactants, agents, products) -> dict` - Name the reaction by the generic template that makes the drawn products from its structures.
- **function**, line 171: `reaction_center(mapped_reaction: str) -> dict` - The reaction centre of an atom-mapped reaction SMILES as a reaction SMARTS.
- **function**, line 223: `reproduces(smarts, reactants, products) -> bool | None` - Whether the template run on ``reactants`` (list of mols) makes one of ``products``; None if it cannot run.
- **function**, line 335: `write_map_numbers(text: str, numbers: dict) -> tuple[str, list]` - (CDXML text with the map numbers added, warnings).

## `route_metrics`

- **function**, line 57: `summarize(raw) -> dict` - No public docstring in the audited version.

## `spectral_text`

- **function**, line 416: `describe(record: dict, mol, label: str) -> dict` - The paragraph (without HRMS) of one compound, with the checks that were run and their warnings.
- **function**, line 235: `distinct_carbons(mol) -> int` - Carbons that differ by symmetry (what a decoupled 13C spectrum can show at most).
- **function**, line 278: `filter_solvent_peaks_1h(peaks: list, solvent: str, tolerance: float = 0.05) -> list` - Filter out 1H residual solvent and HDO peaks from ``peaks`` (numbers, dicts, or peak objects).
- **function**, line 203: `format_peak(peak: dict) -> str` - No public docstring in the audited version.
- **function**, line 211: `format_peaks(peaks) -> str` - No public docstring in the audited version.
- **function**, line 231: `formula_hydrogens(mol) -> int` - No public docstring in the audited version.
- **function**, line 255: `is_solvent_peak_1h(ppm: float, solvent: str, tolerance: float = 0.05) -> dict | None` - Return the matched 1H residual solvent peak dict if ``ppm`` is within ``tolerance``, else ``None``.
- **function**, line 215: `known_multiplicity(mult: str) -> bool` - No public docstring in the audited version.
- **function**, line 180: `normalize_peaks(items, decimals: int) -> list[dict]` - Peaks given as text, numbers or dicts -> the dicts :func:`parse_peaks` returns.
- **function**, line 220: `nucleus_ok(name: str) -> bool` - No public docstring in the audited version.
- **function**, line 154: `parse_peaks(text: str) -> list[dict]` - Peaks of an NMR list such as ``7.40-7.30 (m, 5H), 5.11 (s, 2H)`` as dicts.

## `templates.conformers`

- **function**, line 779: `bicyclic_cage(*, scaffold: str = 'norbornane', substituents: Mapping[int, str] | None = None, cx: float = 180.0, cy: float = 160.0, bond_length: float = 16.0) -> dict[str, Any]` - Generate a 3D perspective bridged cage (norbornane, bicyclo_222, adamantane) with CrossingBonds.
- **function**, line 949: `build_conformer_cdxml(spec: Mapping[str, Any], output_path: str | Path | None = None) -> str` - Dispatch on ``spec['template']`` and return a complete ACS 1996 CDXML document.
- **function**, line 255: `chair_cyclohexane(*, flip: bool = False, substituents: Mapping[int, Mapping[str, str]] | None = None, cx: float = 180.0, cy: float = 160.0, bond_length: float = 14.4) -> dict[str, Any]` - Generate a 6-membered chair cyclohexane (chair1 or ring-flipped chair2).
- **function**, line 662: `fischer_projection(*, centers: Sequence[Mapping[str, str]] = ({'left': 'H', 'right': 'OH'},), top: str = 'CHO', bottom: str = 'CH2OH', cx: float = 180.0, cy: float = 120.0, bond_length: float = 18.0) -> dict[str, Any]` - Generate an orthogonal Fischer projection cross backbone.
- **function**, line 535: `haworth_pyranose(*, anomer: str = 'beta', substituents: Mapping[int, Mapping[str, str]] | None = None, cx: float = 180.0, cy: float = 160.0, bond_length: float = 18.0) -> dict[str, Any]` - Generate a 6-membered Haworth perspective pyranose ring.
- **function**, line 386: `newman_projection(*, conformation: str = 'staggered', dihedral_offset: float | None = None, front: Sequence[str] = ('Me', 'H', 'H'), rear: Sequence[str] = ('Br', 'H', 'Me'), cx: float = 180.0, cy: float = 160.0, bond_length: float = 24.0) -> dict[str, Any]` - Generate a Newman projection (staggered or eclipsed) with circle graphic and perimeter-clipped rear spokes.

## `vision.stereo_audit`

- **function**, line 1172: `audit(cand_smiles: str, reading: dict, image: Image.Image | str | Path | None = None) -> dict | None` - Backward-compatible wrapper around audit_stereo_wedges returning None when unusable.
- **function**, line 1038: `audit_stereo_wedges(candidate_smiles: str, molscribe_reading: dict, image_path: str | Path | Image.Image | None = None) -> dict` - Map candidate_smiles onto molscribe_reading via MCS and return stereocenter agreement/conflict diagnostics.
- **function**, line 1180: `audit_text(a: dict, confidence: float | None = None) -> str` - Format human-readable stereocenter audit report.
- **function**, line 1800: `check_smiles(smiles: str) -> dict` - Validity, canonical form, formula, stereocenters, and warnings of a SMILES.
- **function**, line 333: `cip_labels(mol: Chem.Mol | str) -> dict[int, str]` - Atom index -> R/S (or '?' when unassigned) for each tetrahedral stereocenter.
- **function**, line 763: `compare(a_smiles: str, b_smiles: str, a_name: str = 'yours', b_name: str = 'the reading', stereo: bool = True) -> list[str]` - Plain-language differences between two SMILES; atom indices are those of a_smiles.
- **function**, line 377: `copy_stereo(tgt: Chem.Mol, src: Chem.Mol, s2t: dict[int, int]) -> tuple[Chem.Mol, list[dict]]` - Target molecule (same atom order) carrying the source's tetrahedral stereo over the atom map s2t.
- **function**, line 1558: `depict_like(smiles: str, reference_image_path: str | Path | Image.Image, output_path: str | Path | None = None, annotate_indices: bool = True, *, size: int = 500, annotate: bool | None = None, coords: bool = False)` - Search all 16 rotations/reflections (8 x 45 deg x flip) against reference_image_path ink mask.
- **function**, line 1702: `diagnose_smiles_error(smiles: str) -> SmilesErrorDiagnosis` - Capture RDKit parse errors and pinpoint unclosed parens/brackets, unclosed ring digits, and bare-bracket radicals.
- **function**, line 1883: `edit_structure(smiles: str, ops: list[dict] | None = None, *, set_atom: list[dict] | None = None, set_bond: list[dict] | None = None, add_group: list[dict] | None = None, remove_atoms: list[int] | list[dict] | None = None, set_ez: list[dict] | None = None, set_stereo: list[dict] | dict | None = None) -> EditedSmiles` - Surgical atom-index molecular graph and stereochemistry editor.
- **class**, line 80: `EditedSmiles` - A canonical SMILES string that also supports dict-style metadata lookup.
- **method**, line 97: `EditedSmiles.get(key: str, default = None)` - No public docstring in the audited version.
- **method**, line 100: `EditedSmiles.to_dict() -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 2214: `enumerate_markush_r_groups(core_smiles: str, r_groups_by_label: dict[str, list[str] | str] | list[str] | str)` - Take a [*:1]/[*:2] core SMILES and r_groups_by_label (e.g. {'5a': ['[*:1]F', '[*:2]C']}) and enumerate products via Chem.molzip.
- **function**, line 2318: `find_structures(im: Image.Image | str | Path, min_side: int = 40) -> list[list[int]]` - Candidate boxes [x0, y0, x1, y1] of drawn structures, from connected ink.
- **class**, line 234: `ImageResultDict` - JSON-serializable result dictionary that also proxies PIL.Image.Image attributes.
- **property**, line 242: `ImageResultDict.image` - No public docstring in the audited version.
- **function**, line 1525: `ink(im: Image.Image, n: int = 64) -> np.ndarray` - No public docstring in the audited version.
- **class**, line 295: `MarkushEnumerationResult` - Dictionary mapping label -> canonical SMILES while also exposing .products/.results metadata.
- **method**, line 309: `MarkushEnumerationResult.get(key, default = None)` - No public docstring in the audited version.
- **function**, line 346: `mcs_map(tgt: Chem.Mol, src: Chem.Mol, timeout: int = 20) -> tuple[dict[int, int], int]` - Source atom index -> target atom index over the maximum common substructure, and its size.
- **function**, line 701: `mol_key(mol: Chem.Mol, stereo: bool = True) -> str` - Identity key of a molecule: InChIKey or canonical SMILES when dummy atoms are present.
- **function**, line 823: `ms_mol(reading: dict) -> tuple[Chem.Mol | None, np.ndarray | None]` - Convert a MolScribe reading dict into an RDKit molecule and per-atom (x, y) pixel array.
- **function**, line 1316: `overlay(crop: Image.Image, a: dict, max_patches: int = 4) -> Image.Image | None` - Candidate bonds drawn at MolScribe's atom positions over the washed-out crop plus zoomed conflict patches.
- **function**, line 1370: `read_wedges(smiles: str, wedges: list[dict], positions: list[dict[int, tuple[float, float]]] | dict[int, tuple[float, float]] | None = None) -> ReadWedgesResult` - Set stereocenters in smiles from visual wedges and return canonical SMILES + per-center CIP labels.
- **function**, line 753: `reader_labels(yours: str, reader: str) -> dict[int, str] | None` - CIP label each stereocentre of yours has in reader's SMILES; None when skeletons differ.
- **class**, line 209: `ReadWedgesResult` - Result of read_wedges(smiles, wedges), usable as dict or unpacked as (smiles, cip_labels).
- **function**, line 1322: `render_diff_overlay(image_path: str | Path | Image.Image, candidate_smiles: str, molscribe_reading: dict, output_path: str | Path | None = None) -> ImageResultDict` - Render green (shared), red (candidate-only), and blue (reading-only) bond overlays plus 240x240 patches.
- **function**, line 1778: `smiles_warnings(mol: Chem.Mol, centers = None) -> list[str]` - Things that parse in RDKit but are almost never what a journal figure shows.
- **class**, line 104: `SmilesErrorDiagnosis` - Diagnostic string from diagnose_smiles_error that also exposes structured fields.
- **method**, line 125: `SmilesErrorDiagnosis.get(key: str, default = None)` - No public docstring in the audited version.
- **method**, line 128: `SmilesErrorDiagnosis.to_dict() -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 985: `snap(image: Image.Image | str | Path, mol: Chem.Mol, xy: np.ndarray) -> np.ndarray` - MolScribe atom positions moved onto the drawn bonds.
- **function**, line 939: `snap_with(image_path: str | Path | Image.Image, atoms: list[dict[str, Any]] | Chem.Mol | np.ndarray, bonds: list[dict[str, Any]] | np.ndarray, extra: np.ndarray | None = None)` - Align MolScribe 2D atom coordinates onto dark bond ink in image_path.
- **class**, line 256: `SnappedPoint` - 2D atom coordinate supporting both point['x']/point['y'] and point[0]/point[1].
- **class**, line 277: `SnappedPointsList` - List of SnappedPoint entries that also behaves like an (N, 2) numpy float array.
- **property**, line 281: `SnappedPointsList.shape` - No public docstring in the audited version.
- **function**, line 715: `stereo_compare(cand: Chem.Mol, src: Chem.Mol, s2t: dict[int, int]) -> list[dict]` - Per candidate stereocenter: compare implied source label with candidate's own label.
- **function**, line 631: `stereo_from_wedges(atoms: list[dict[str, Any]] | str, bonds: list[dict[str, Any]] | dict[int, dict[int, tuple]], *, flip_y: bool = True) -> StereoFromWedgesResult | str` - Build an RDKit 2D conformer from MolScribe (x, y) + wedges and extract per-atom (R/S, confidence).
- **function**, line 1511: `stereo_notes(smiles: str) -> list[str]` - 'atom 3 C: R' for each stereocenter, in the atom order of smiles.
- **class**, line 132: `StereoFromWedgesResult` - Result of stereo_from_wedges(atoms, bonds), supporting both dict keys and atom-index lookup.
- **property**, line 140: `StereoFromWedgesResult.mol` - No public docstring in the audited version.
- **function**, line 428: `transfer_stereo(src_mol: Chem.Mol | str, dst_mol: Chem.Mol | str, timeout: int = 20) -> TransferStereoResult` - Transfer tetrahedral stereocenters from src_mol onto dst_mol over their MCS map.
- **class**, line 163: `TransferStereoResult` - Result of transfer_stereo, usable as dict, (smiles, report) tuple, or RDKit Mol proxy.
- **property**, line 176: `TransferStereoResult.mol` - No public docstring in the audited version.
- **function**, line 2115: `visual_checkpoints(smiles: str, limit: int = 12) -> list[str]` - Flag terminal =CH2, Si carbon counts (TMS/TES/TBS/TIPS), and benzene ortho/meta/para substitution indices.
