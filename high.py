
import os

def High(fname,limit=10):

    return Highs(fname,limit)['default']
    
class _Score:
    def __init__(self,score,name,data=None):
        self.score,self.name,self.data=score,name,data
    
class _High:

    
    def __init__(self,highs,limit=10):
        self.highs = highs
        self._list = []
        self.limit = limit
        
    def save(self):
        self.highs.save()
        
    def submit(self,score,name,data=None):
        n = 0
        for e in self._list:
            if score > e.score:
                self._list.insert(n,_Score(score,name,data))
                self._list = self._list[0:self.limit]
                return n
            n += 1
        if len(self._list) < self.limit:
            self._list.append(_Score(score,name,data))
            return len(self._list)-1
    
    def check(self,score):
        n = 0
        for e in self._list:
            if score > e.score:
                return n
            n += 1
        if len(self._list) < self.limit:
            return len(self._list)
        
        
    def __iter__(self):
        return self._list.__iter__()
        
    def __getitem__(self,key):
        return self._list[key]
        
    def __len__(self):
        return self._list.__len__()
        

class Highs:
    def __init__(self,fname,limit=10):
        self.fname = fname
        self.limit = limit
        self.load()
        
    def load(self):
        self._dict = {}
        try:
            f = open(self.fname)
            for line in f.readlines():
                key,score,name,data = line.strip().split(",")
                if key not in self._dict:
                    self._dict[key] = _High(self,self.limit)
                high = self._dict[key]
                high.submit(int(score),name,data)
            f.close()
        except:
            pass
    
    def save(self):
        f = open(self.fname,"w")
        for key,high in self._dict.items():
            for e in high:
                f.write("%s,%d,%s,%s\n"%(key,e.score,e.name,str(e.data)))
        f.close()
        
    def __getitem__(self,key):
        if key not in self._dict:
            self._dict[key] = _High(self,self.limit)
        return self._dict[key]
