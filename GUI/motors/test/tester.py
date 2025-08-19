from typing import ClassVar

class Foo():
    var : ClassVar[int] = 0
    varCount : ClassVar[list] = []

    def __init__(self):
        print("Initialization")
        
        for i in range(10):
            Foo.var += 1
        
        print(Foo.var)

        self._foo = Foo.var
        Foo.varCount.append(self._foo)
    
    def some_method(self):
        print("this is some method")
        Foo.var += 1

def main():
    FooInstance1 = Foo()
    FooInstance2 = Foo()
    FooInstance2.some_method()

    print(f"var: {FooInstance1.var}, {FooInstance2.var}\n varCount: {FooInstance1.varCount}, {FooInstance2.varCount}")

if __name__ == '__main__':
    main()