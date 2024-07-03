class trieNode:
    def __init__(self):
        self.Index = 0
        self.Index = 0
        self.Layer = 0
        self.End = False
        self.Char = ""
        self.Results = []
        self.m_values = {}
        self.Failure = None
        self.Parent = None

    def Add(self, c):
        if c in self.m_values:
            return self.m_values[c]
        node = trieNode()
        node.Parent = self
        node.Char = c
        self.m_values[c] = node
        return node

    def SetResults(self, index):
        if not self.End:
            self.End = True
        self.Results.append(index)
