class hashNode:
    def __init__(self):
        self.End = False
        self.Results = []
        self.m_values = {}
        self.min_flag = 0xFFFF
        self.max_flag = 0

    def Add(self, c, node3):
        if self.min_flag > c:
            self.min_flag = c
        if self.max_flag < c:
            self.max_flag = c
        self.m_values[c] = node3

    def SetResults(self, index):
        if not self.End:
            self.End = True
        if not (index in self.Results):
            self.Results.append(index)

    def HasKey(self, c):
        return c in self.m_values

    def TryGetValue(self, c):
        if self.min_flag <= c <= self.max_flag:
            if c in self.m_values:
                return self.m_values[c]
        return None
