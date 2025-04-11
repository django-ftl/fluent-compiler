"""
Compatibility module for generating Python AST.

The interface mocks the stdlib 'ast' module of the most recent Python version
we support. Our codegen module then is written as if it targets that version.
When necessary for older Python versions, this module can provide wrappers that
convert the new-style AST used by codegen.py into the old-style AST used by the
Python version.

If a new Python version changes/breaks the AST for existing features, the process is:

- change this module and codegen.py to use the new AST, get it working on
  latest version of Python.

- add blocks something like the following as necessary to get it working on older
  versions of Python:

  if sys.version_info < (...):
      def NewAst(...):
          return ast.OldAst(...)

  else:
      NewAst = ast.NewAst

"""
import ast

# This is a very limited subset of Python AST:
# - only the things needed by codegen.py
# - only syntax features provided by the oldest Python version we support

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
Or = ast.Or
Pass = ast.Pass
Return = ast.Return
Store = ast.Store
Subscript = ast.Subscript
Tuple = ast.Tuple
arguments = ast.arguments
JoinedStr = ast.JoinedStr
FormattedValue = ast.FormattedValue
Attribute = ast.Attribute
Call = ast.Call
FunctionDef = ast.FunctionDef
Name = ast.Name
Try = ast.Try
arg = ast.arg
keyword = ast.keyword
walk = ast.walk
Constant = ast.Constant
AST = ast.AST
