def infer_architecture(files: list[str]) -> dict:
    layers = {
        "api": [],
        "services": [],
        "db": [],
        "utils": [],
        "other": []
    }

    for f in files:
        if "/api/" in f:
            layers["api"].append(f)
        elif "/services/" in f:
            layers["services"].append(f)
        elif "/db/" in f:
            layers["db"].append(f)
        elif "/utils/" in f:
            layers["utils"].append(f)
        else:
            layers["other"].append(f)

    return layers
