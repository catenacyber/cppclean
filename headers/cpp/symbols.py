#!/usr/bin/env python
#
# Copyright 2007 Neal Norwitz
# Portions Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Symbol Table utility code."""

__author__ = 'nnorwitz@google.com (Neal Norwitz)'


if 'BaseException' not in dir(__builtins__):
    # Support Python 2.4 and earlier.
    BaseException = Exception


class Error(BaseException):
    """Exception raised when lookup fails."""


class Symbol(object):
    """Data container used internally."""

    def __init__(self, name, parts, namespace_stack):
        self.name = name
        self.parts = parts
        self.namespace_stack = namespace_stack


class SymbolTable(object):
    """Symbol table that can perform namespace operations."""

    def __init__(self):
        # None is the global namespace.
        self.namespaces = {None: {}}

    def _LookupNamespace(self, symbol, namespace, kind):
        """Helper for LookupSymbol that only looks up global variables.

        Args:
          symbol: Symbol
          namespace: pointer into self.namespaces
          kind: 'kind of namespace for error message'
        """
        for namespace_part in symbol.parts:
            if not isinstance(namespace, dict):
                raise Error('%s found non-namespace entry before %s' %
                            (symbol.name, namespace_part))
            namespace = namespace.get(namespace_part)
            if namespace is None:
                raise Error('%s not found in %snamespace at %s' %
                            (symbol.name, kind, namespace_part))
            result = namespace
        return result

    def _LookupGlobal(self, symbol):
        """Helper for LookupSymbol that only looks up global variables.

        Args:
          symbol: Symbol
        """
        assert symbol.parts
        namespace = self.namespaces
        if len(symbol.parts) == 1:
            # If there is only one part, look in globals.
            namespace = self.namespaces[None]
        return self._LookupNamespace(symbol, namespace, 'global ')

    def _LookupInAllNamespaces(self, symbol):
        """Helper for LookupSymbol that looks for symbols in all namespaces.

        Args:
          symbol: Symbol
        """
        namespace = self.namespaces
        # Create a stack of namespaces.
        namespace_stack = []
        for current in symbol.namespace_stack:
            namespace = namespace.get(current)
            if namespace is None or not isinstance(namespace, dict):
                break
            namespace_stack.append(namespace)

        # Iterate through the stack in reverse order.  Need to go from
        # innermost namespace to outermost.
        for namespace in reversed(namespace_stack):
            try:
                return self._LookupNamespace(symbol, namespace, '')
            except Error:
                pass
        return None

    def LookupSymbol(self, name, namespace_stack):
        """Returns AST node and module for symbol if found.

        Args:
          name: 'name of the symbol to lookup'
          namespace_stack: None or ['namespaces', 'in', 'current', 'scope']

        Returns:
          (ast.Node, module (ie, any object stored with symbol)) if found

        Raises:
          Error if the symbol cannot be found.
        """
        # TODO(nnorwitz): a convenient API for this depends on the
        # representation of the name.  e.g., does symbol_name contain
        # ::, is symbol_name a list of colon separated names, how are
        # names prefixed with :: handled.  These have different lookup
        # semantics (if leading ::) or change the desirable API.

        # For now assume that the symbol_name contains :: and parse it.
        symbol = Symbol(name, name.split('::'), namespace_stack)
        assert symbol.parts
        if symbol.parts[0] == '':
            # Handle absolute (global) ::symbol_names.
            symbol.parts = symbol.parts[1:]
            return self._LookupGlobal(symbol)

        if namespace_stack is not None:
            result = self._LookupInAllNamespaces(symbol)
            if result:
                return result

        return self._LookupGlobal(symbol)

    def _Add(self, symbol_name, namespace, node, module):
        """Helper function for adding symbols.  See AddSymbol()."""
        result = symbol_name in namespace
        namespace[symbol_name] = node, module
        return not result
            
    def AddSymbol(self, symbol_name, namespace_stack, node, module):
        """Adds symbol_name defined in namespace_stack to the symbol table.

        Args:
          symbol_name: 'name of the symbol to lookup'
          namespace_stack: None or ['namespaces', 'defined', 'in']
          node: ast.Node that defines this symbol
          module: module (any object) this symbol is defined in

        Returns:
          bool(if symbol was *not* already present)
        """
        # TODO(nnorwitz): verify symbol_name doesn't contain :: ?
        if namespace_stack is not None:
            # Handle non-global symbols (ie, in some namespace).
            assert namespace_stack, 'namespace_stack must not be empty'
            last_namespace = self.namespaces
            for namespace in namespace_stack:
                last_namespace = last_namespace.setdefault(namespace, {})
        else:
            last_namespace = self.namespaces[None]
        return self._Add(symbol_name, last_namespace, node, module)