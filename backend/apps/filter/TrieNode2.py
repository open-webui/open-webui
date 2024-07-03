class TrieNode2():
    def __init__(self):
        self.End = False
        self.Results = []
        self.m_values = {}
        self.minflag = 0xffff
        self.maxflag = 0

    def Add(self, c, node3):
        if self.minflag > c:
            self.minflag = c
        if self.maxflag < c:
            self.maxflag = c
        self.m_values[c] = node3

    def SetResults(self, index):
        if not self.End:
            self.End = True
        if not (index in self.Results):
            self.Results.append(index)

    def HasKey(self, c):
        return c in self.m_values

    def TryGetValue(self, c):
        if self.minflag <= c <= self.maxflag:
            if c in self.m_values:
                return self.m_values[c]
        return None