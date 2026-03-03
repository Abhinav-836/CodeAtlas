def generate_diagram(architecture: dict) -> dict:
    return {
        "nodes": list(architecture.keys()),
        "edges": []
    }
