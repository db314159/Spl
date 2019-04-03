
class Character:
    def __init__(self, startingvalue, name):
        self.value = startingvalue
        self.name = name
        self.stack = []
        
    def push(self,value):
        self.stack.append(value)
        
    def pop(self):
        self.value = self.stack.pop()
        
class ActChange(Exception):
    pass
    
class SceneChange(Exception):
    pass
    
def isqrt(num):
    return int(sqrt(num))
    
def square(num):
    return num**2
    
def twice(num):
    return num*2
    
def cube(num):
    return num**3
    