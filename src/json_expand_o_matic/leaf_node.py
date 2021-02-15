import enum
import re


class LeafNode:
    """Identifies a leaf node during json traversal and what to
    do if that leaf node is encoutered.
    """

    # > -- create something.json
    # < -- embed into parent
    # B -- process pattern Before recursion
    # A -- process pattern After recursion
    # F -- Format the patern in formatAndReCompile()
    # f -- do not Format the pattern
    # P -- Precompile the pattern during construct()
    # p -- do not Precompile the pattern
    #   -- (space) no-op
    #
    # If '{' is present in the pattern, 'F' and 'p'
    # are assumed unless overridden.
    #
    # If mutually exclusive commands are present,
    # the last one wins.
    command_and_expression = re.compile("^([ ><BAp]+:)?(.*)$")

    class What(enum.Enum):
        DUMP = 1
        INCLUDE = 2

    class When(enum.Enum):
        BEFORE = "B"
        AFTER = "A"

    def __init__(self, *args, **kwargs):
        pass

    def match(self, string):
        """Compare _string_ to our compiled regex."""
        return self.compiled.match(string)

    def format(self, **context):
        """Apply the context to our pattern and recompile."""
        intermediate = self.pattern.format(**context) if self.FORMAT else self.pattern
        self.compiled = re.compile(intermediate)

    def recompile(self):
        """Recompile the original pattern (removes formatting)."""
        self.compiled = re.compile(self.pattern)

    @classmethod
    def construct(cls, data):
        """Construct one or more LeafNode instances from _data_.

        If _data_ is a LeafNode return a list with just it.
        If _data_ is a string return a list with one LeafNode.
        If _data_ is a dict return a list with one or more LeafNodes.
        """

        if isinstance(data, LeafNode):
            return [data]

        if not isinstance(data, str) and not isinstance(data, dict):
            raise Exception(f"Illegal type for leaf-node: {type(data)} : {data}")

        if isinstance(data, dict):
            result = []
            for key, value in data.items():
                r = LeafNode.construct(key)[0]
                result.append(r)

                for child in value:
                    r.children.extend(LeafNode.construct(child))

            return result

        # Else, must be a str

        m = LeafNode.command_and_expression.match(data)

        r = LeafNode()
        r.raw = data
        r.children = []
        r.commands = m.group(1) if m.group(1) else ""
        r.pattern = m.group(2) if m.group(2) else ""
        r.compiled = None
        r.WHAT = LeafNode.What.DUMP
        r.WHEN = LeafNode.When.BEFORE
        r.FORMAT = False
        r.PRECOMPILE = True

        if "{" in r.pattern:
            r.FORMAT = True
            r.PRECOMPILE = False

        for c in r.commands:
            if c in [" ", ":"]:
                pass
            elif c is ">":
                r.WHAT = LeafNode.What.DUMP
            elif c is "<":
                r.WHAT = LeafNode.What.INCLUDE
            elif c is "B":
                r.WHEN = LeafNode.When.BEFORE
            elif c is "A":
                r.WHEN = LeafNode.When.AFTER
            elif c is "P":
                r.PRECOMPILE = True
            elif c is "p":
                r.PRECOMPILE = False
            elif c is "F":
                r.FORMAT = True
            elif c is "f":
                r.FORMAT = False

        if r.PRECOMPILE:
            r.compiled = re.compile(r.pattern)

        return [r]