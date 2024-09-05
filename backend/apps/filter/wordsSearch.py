from open_webui.apps.filter.hashNode import hashNode
from open_webui.apps.filter.trieNode import trieNode


class wordsSearch:
    def __init__(self):
        self._first = {}
        self._keywords = []
        self._indexs = []

    def SetKeywords(self, keywords):
        self._keywords = keywords
        self._indexs = []
        for i in range(len(keywords)):
            self._indexs.append(i)

        root = trieNode()
        allNodeLayer = {}

        for i in range(len(self._keywords)):
            p = self._keywords[i]
            nd = root
            for j in range(len(p)):
                nd = nd.Add(ord(p[j]))
                if nd.Layer == 0:
                    nd.Layer = j + 1
                    if nd.Layer in allNodeLayer:
                        allNodeLayer[nd.Layer].append(nd)
                    else:
                        allNodeLayer[nd.Layer] = []
                        allNodeLayer[nd.Layer].append(nd)
            nd.SetResults(i)

        allNode = [root]
        for key in allNodeLayer.keys():
            for nd in allNodeLayer[key]:
                allNode.append(nd)

        for i in range(len(allNode)):
            if i == 0:
                continue
            nd = allNode[i]
            nd.Index = i
            r = nd.Parent.Failure
            c = nd.Char
            while r is not None and (c in r.m_values) == False:
                r = r.Failure
            if r is None:
                nd.Failure = root
            else:
                nd.Failure = r.m_values[c]
                for key2 in nd.Failure.Results:
                    nd.SetResults(key2)
        root.Failure = root

        allNode2 = []
        for i in range(len(allNode)):
            allNode2.append(hashNode())

        for i in range(len(allNode2)):
            oldNode = allNode[i]
            newNode = allNode2[i]

            for key in oldNode.m_values:
                index = oldNode.m_values[key].Index
                newNode.Add(key, allNode2[index])

            for index in range(len(oldNode.Results)):
                item = oldNode.Results[index]
                newNode.SetResults(item)

            oldNode = oldNode.Failure
            while oldNode != root:
                for key in oldNode.m_values:
                    if not newNode.HasKey(key):
                        index = oldNode.m_values[key].Index
                        newNode.Add(key, allNode2[index])
                for index in range(len(oldNode.Results)):
                    item = oldNode.Results[index]
                    newNode.SetResults(item)
                oldNode = oldNode.Failure

        self._first = allNode2[0]

    def FindFirst(self, text):
        ptr = None
        for index in range(len(text)):
            t = ord(text[index])
            tn = None
            if ptr is None:
                tn = self._first.TryGetValue(t)
            else:
                tn = ptr.TryGetValue(t)
                if tn is None:
                    tn = self._first.TryGetValue(t)

            if tn is not None:
                if tn.End:
                    item = tn.Results[0]
                    keyword = self._keywords[item]
                    return {
                        "Keyword": keyword,
                        "Success": True,
                        "End": index,
                        "Start": index + 1 - len(keyword),
                        "Index": self._indexs[item],
                    }
            ptr = tn
        return None

    def FindAll(self, text):
        ptr = None
        key_list = []

        for index in range(len(text)):
            t = ord(text[index])
            tn = None
            if ptr is None:
                tn = self._first.TryGetValue(t)
            else:
                tn = ptr.TryGetValue(t)
                if tn is None:
                    tn = self._first.TryGetValue(t)

            if tn is not None:
                if tn.End:
                    for j in range(len(tn.Results)):
                        item = tn.Results[j]
                        keyword = self._keywords[item]
                        key_list.append(
                            {
                                "Keyword": keyword,
                                "Success": True,
                                "End": index,
                                "Start": index + 1 - len(keyword),
                                "Index": self._indexs[item],
                            }
                        )
            ptr = tn
        return key_list

    def ContainsAny(self, text):
        ptr = None
        for index in range(len(text)):
            t = ord(text[index])
            tn = None
            if ptr is None:
                tn = self._first.TryGetValue(t)
            else:
                tn = ptr.TryGetValue(t)
                if tn is None:
                    tn = self._first.TryGetValue(t)

            if tn is not None:
                if tn.End:
                    return True
            ptr = tn
        return False

    def Replace(self, text, replaceChar="*"):
        result = list(text)

        ptr = None
        for i in range(len(text)):
            t = ord(text[i])
            tn = None
            if ptr is None:
                tn = self._first.TryGetValue(t)
            else:
                tn = ptr.TryGetValue(t)
                if tn is None:
                    tn = self._first.TryGetValue(t)

            if tn is not None:
                if tn.End:
                    maxLength = len(self._keywords[tn.Results[0]])
                    start = i + 1 - maxLength
                    for j in range(start, i + 1):
                        result[j] = replaceChar
            ptr = tn
        return "".join(result)
