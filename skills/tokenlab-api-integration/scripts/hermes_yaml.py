"""Insert one Hermes provider using YAML source marks; never serialize existing settings."""

import copy
import json

from setup_files import SetupError

# Each tested Hermes release and the YAML parser its official installation ships.
# 0.21.3 bundles PyYAML; 0.21.6 replaced it with ruamel.yaml (Python 3.14 runtime).
PARSERS = {"0.21.3": ("PyYAML", "6.0.3"), "0.21.6": ("ruamel.yaml", "0.18.16")}


def parser_for(version: str) -> str:
    if version not in PARSERS:
        raise SetupError("This helper targets Hermes 0.21.3 or 0.21.6. Use the manual guide for other versions.")
    return PARSERS[version][0]


def _pyyaml():
    try:
        import yaml
    except ImportError:
        raise SetupError("PyYAML is unavailable. Run with your installed Hermes Python or use --hermes-python; no packages were installed.") from None
    if yaml.__version__ != "6.0.3":
        raise SetupError("Use the PyYAML 6.0.3 environment supplied by Hermes 0.21.3; no packages were installed.")

    def compose(text):
        return yaml.compose(text, Loader=yaml.SafeLoader)

    def load(text):
        return yaml.load(text, Loader=yaml.SafeLoader)

    return compose, load, yaml.YAMLError


def _ruamel():
    try:
        from ruamel.yaml import YAML, __version__
        from ruamel.yaml.error import YAMLError
    except ImportError:
        raise SetupError("ruamel.yaml is unavailable. Run with your installed Hermes Python or use --hermes-python; no packages were installed.") from None
    if __version__ != "0.18.16":
        raise SetupError("Use the ruamel.yaml 0.18.16 environment supplied by Hermes 0.21.6; no packages were installed.")

    def parser():
        # Match Hermes 0.21.6 (hermes_yaml.safe_load): safe schema, YAML 1.1
        # booleans, pure parser. A fresh instance per operation.
        instance = YAML(typ="safe", pure=True)
        instance.version = (1, 1)
        return instance

    def compose(text):
        return parser().compose(text)

    def load(text):
        return parser().load(text)

    return compose, load, YAMLError


def _check_unique(node, seen=None):
    # Merge keys can hide a collision and change an alias consumer. Checked on
    # the composed node tree so both parsers apply exactly the same rule.
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    if node.tag == "tag:yaml.org,2002:map":
        keys = set()
        for key, value in node.value:
            if key.tag != "tag:yaml.org,2002:str" or not isinstance(key.value, str) or key.value in keys:
                raise ValueError("Ambiguous YAML mapping")
            keys.add(key.value)
            _check_unique(value, seen)
    elif isinstance(node.value, list):
        for item in node.value:
            _check_unique(item, seen)


def _backend(parser: str | None):
    if parser == "PyYAML":
        return _pyyaml()
    if parser == "ruamel.yaml":
        return _ruamel()
    if parser is not None:
        raise SetupError("Unsupported YAML parser selection; no settings were changed.")
    # No Hermes version was given (direct library use): prefer PyYAML 6.0.3,
    # otherwise the ruamel.yaml 0.18.16 runtime of Hermes 0.21.6.
    try:
        return _pyyaml()
    except SetupError:
        try:
            return _ruamel()
        except SetupError:
            raise SetupError("Neither PyYAML 6.0.3 (Hermes 0.21.3) nor ruamel.yaml 0.18.16 (Hermes 0.21.6) is available. "
                             "Run with your installed Hermes Python or use --hermes-python; no packages were installed.") from None


def insert_provider(content: bytes | None, container: str, name: str, provider: dict, parser: str | None = None) -> bytes:
    # Use the parser already installed by the pinned official Hermes distribution.
    # Import lazily so restoration continues to work after Hermes is uninstalled.
    compose, load, yaml_error = _backend(parser)

    try:
        text = (content or b"").decode("utf-8")
        root = compose(text)
        _check_unique(root)
        document = load(text)
        if root is None:
            document = {}
        if not isinstance(document, dict):
            raise ValueError("Expected a mapping")
        selected = document.get("model", {})
        if isinstance(selected, dict) and selected.get("provider") in {name, f"custom:{name}"}:
            raise SetupError("The existing default already refers to that Hermes provider; choose another name.")
        existing = document.get(container, {})
        if not isinstance(existing, dict):
            raise ValueError("Expected providers mapping")
        if name in existing:
            raise SetupError("That Hermes provider already exists outside this helper. Choose another provider name.")
        target = root
        addition = {container: {name: provider}}
        if container in document:
            target = next(value for key, value in root.value if key.value == container)
            addition = {name: provider}
        newline = "\r\n" if "\r\n" in text else "\n"
        if target is not None and target.flow_style:
            # Flow mappings use JSON-compatible member syntax. Keep all old bytes.
            offset = target.end_mark.index - 1
            if text[offset] != "}":
                raise ValueError("Unexpected flow mapping")
            fragment = (", " if target.value else "") + json.dumps(addition, ensure_ascii=False)[1:-1]
        else:
            offset = target.end_mark.index if target is not None else len(text)
            indent = target.start_mark.column if target is not None else 0
            # Existing mapping ends at the next sibling token; insert before its
            # indentation, including when it is the root document-end marker.
            line_start = text.rfind("\n", 0, offset) + 1
            if not text[line_start:offset].strip():
                offset = line_start
            prefix = " " * indent
            if container in document:
                lines = [prefix + json.dumps(name) + ":"]
                lines += [prefix + "  " + json.dumps(key) + ": " + json.dumps(value)
                          for key, value in provider.items()]
            else:
                lines = [prefix + container + ":", prefix + "  " + json.dumps(name) + ":"]
                lines += [prefix + "    " + json.dumps(key) + ": " + json.dumps(value)
                          for key, value in provider.items()]
            fragment = (newline if offset and text[offset - 1] not in "\r\n\ufeff" else "") + newline.join(lines) + newline
        result = text[:offset] + fragment + text[offset:]
        _check_unique(compose(result))
        loaded = load(result)
        expected = copy.deepcopy(document)
        # Replace just this mapping in the expected value. Shared YAML aliases
        # elsewhere must not gain a provider as a side effect of insertion.
        expected[container] = {**copy.deepcopy(existing), name: provider}
        if loaded != expected:
            raise ValueError("Insertion changed other settings")
        return result.encode("utf-8")
    except SetupError:
        raise
    except (yaml_error, ValueError, TypeError, UnicodeDecodeError, RecursionError, AttributeError, StopIteration):
        raise SetupError("Hermes configuration is not an unambiguous supported YAML mapping; use the manual guide. Existing values were not printed or changed.") from None
