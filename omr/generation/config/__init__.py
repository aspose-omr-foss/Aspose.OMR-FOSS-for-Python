"""Code-first configuration tree — core abstractions.

Port of ``Aspose.OMR.Generation.Config``. Every node derives from ``BaseConfig``;
nodes that can hold children derive from ``ParentConfig``. Each concrete config's
constructor auto-initializes ``Type`` to its matching ``ConfigType`` value.
"""
from __future__ import annotations

from omr.generation.config.enums import ConfigType

__all__ = ["BaseConfig", "ParentConfig", "TemplateConfig", "BorderStyle"]


class BaseConfig:
    """Root abstraction; the required fields of every OMR element.

    ``Name`` meaning varies per element; ``Type`` is the ``ConfigType`` discriminator
    each subclass sets in its constructor.
    """

    def __init__(self) -> None:
        self.Name: str = ""
        self.Type: ConfigType | None = None


class ParentConfig(BaseConfig):
    """Marks an element that can contain children."""

    def __init__(self) -> None:
        super().__init__()
        self.Children: list[BaseConfig] = []


class TemplateConfig(ParentConfig):
    """The document root that contains everything else (normally ``PageConfig``s)."""

    def __init__(self) -> None:
        super().__init__()
        self.Type = ConfigType.Template


class BorderStyle:
    """Describes the border of ONE side of an element. Assigned to the
    ``Border*Style`` properties on ``BlockConfig`` / ``InputGroup`` /
    ``CustomAnswerSheetConfig`` / ``TableTitleConfig``. Plain class, NOT a BaseConfig.
    """

    def __init__(self) -> None:
        # Imported lazily-at-use to avoid a hard import cycle at module load.
        from omr.generation import Color

        self.BorderColor: "Color" = Color.Black
        self.BorderSize: int = 3
        self.Disable: bool = False
