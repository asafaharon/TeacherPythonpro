export const modulesExamples = [
    {id: 1, examples: ["print('שלום עולם')"]},
    {id: 2, examples: ["x = 5\nprint(type(x))"]},
    {id: 3, examples: ["name = input('הכנס שם: ')\nprint('שלום', name)"]},
    {id: 4, examples: ["a, b = 5, 3\nprint(a + b)\nprint(a > b)"]},
    {id: 5, examples: ["x = 10\nif x > 5:\n    print('גדול מ-5')"]},
    {id: 6, examples: ["for i in range(5):\n    print(i)"]},
    {id: 7, examples: ["s = 'Python'\nprint(s.lower())"]},
    {id: 8, examples: ["lst = [1,2,3]\nlst.append(4)\nprint(lst)"]},
    {id: 9, examples: ["t = (1,2,3)\ns = {1,2,3}\nprint(len(s))"]},
    {id: 10, examples: ["d = {'a':1}\nprint(d['a'])"]},
    {id: 11, examples: ["def hello(name):\n    return 'Hi ' + name"]},
    {id: 12, examples: ["try:\n    1/0\nexcept ZeroDivisionError:\n    print('שגיאה')"]},
    {id: 13, examples: ["with open('test.txt','w') as f:\n    f.write('hello')"]},
    {id: 14, examples: ["class Dog:\n    def bark(self):\n        print('woof')"]},
    {id: 15, examples: ["def fact(n):\n    return 1 if n==0 else n*fact(n-1)"]}
];
