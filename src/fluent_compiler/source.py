from __future__ import annotations

from fluent.syntax import ast as fl_ast

from .resource import FtlResource
from .utils import (
    span_to_position,
)


class FtlSource:
    """
    Object used to specify the origin of a chunk of FTL
    """

    def __init__(self, ast_node: fl_ast.Attribute | fl_ast.Message, ftl_resource: FtlResource):
        self.ast_node = ast_node
        self.ftl_resource = ftl_resource
        self.filename = self.ftl_resource.filename
        assert ast_node.span is not None
        self.row, self.column = span_to_position(ast_node.span, ftl_resource.text)
