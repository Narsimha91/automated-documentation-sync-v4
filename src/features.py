"""Ordered source of features maintained in the project README."""


def features() -> list[str]:
    return [
        "Maintains an ordered Python source for README features",
        "Validates README markers before changing generated content",
        "Preserves README content outside generated feature bullets",
        "Skips writes when generated content is unchanged",
    ]