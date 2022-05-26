"""
Compatibility module for generating Python AST.

The interface mocks the stdlib 'ast' module of the most recent Python version we
support, so that the codegen module can be written as if it targets that
version. For older versions we provide shims that adapt to the older AST as and
when necessary.

"""
import ast

# We include only the things codegen needs.
Add = ast.Add
Assign = ast.Assign
BoolOp = ast.BoolOp
BinOp = ast.BinOp
Compare = ast.Compare
Dict = ast.Dict
Eq = ast.Eq
ExceptHandler = ast.ExceptHandler
Expr = ast.Expr
If = ast.If
Index = ast.Index
List = ast.List
Load = ast.Load
Module = ast.Module
Num = ast.Num
Or = ast.Or
Pass = ast.Pass
Return = ast.Return
Store = ast.Store
Str = ast.Str
Subscript = ast.Subscript
Tuple = ast.Tuple
arguments = ast.arguments
JoinedStr = ast.JoinedStr
FormattedValue = ast.FormattedValue
Attribute = ast.Attribute
Call = ast.Call
FunctionDef = ast.FunctionDef
Name = ast.Name
NameConstant = ast.NameConstant
Try = ast.Try
arg = ast.arg
keyword = ast.keyword


def traverse(ast_node, func):
    """
    Apply 'func' to ast_node (which is `ast.*` object)
    """
    for node in ast.walk(ast_node):
        func(node)
