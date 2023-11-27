# Example of a abstract machine interface.

from abc import abstractmethod, ABC
from inspect import signature
from collections import deque
from typing import Deque, Dict, Any


ENVIRONMENT: Dict[str, Any] = {}

class Engine:

    def __init__(self):
        self.value_stack = []
        self.code = ()
        self.pc = 0
        self.locals = {}
        self.globals = ENVIRONMENT
        self.dump = []

    def run(self):
        while self.pc < len(self.code):
            print(f'PC: {self.pc} CODE: {self.code[self.pc]}')
            L = self.code[self.pc]
            self.pc += 1
            L(self)

    def returnValues(self):
        return tuple(self.value_stack)

    def callq(self, fn: 'Function'):
        self.dump.append(self.code)
        self.dump.append(self.pc)
        self.code = fn.code()
        self.pc = 0

    def sys_callq_Nto1(self, nargs, fn):
        d: Deque = deque()
        for _ in range(nargs):
            d.appendleft(self.value_stack.pop())
        self.value_stack.append(fn(*d))

    def sys_callq_2to1(self, fn):
        y = self.value_stack.pop()
        x = self.value_stack.pop()
        self.value_stack.append(fn(x, y))

    def pushq(self, value):
        self.value_stack.append(value)

def inst_leave(engine: Engine):
    engine.locals = engine.dump.pop()
    engine.pc = engine.dump.pop()
    engine.code = engine.dump.pop()

def inst_enter(engine: Engine):
    engine.dump.append(engine.locals)
    engine.locals = {}

def inst_callq(engine: Engine, fn: 'Function'):
    engine.dump.append(engine.code)
    engine.dump.append(engine.pc)
    engine.code = fn.code()
    engine.pc = 0

def inst_sys_callq_Nto1(engine: Engine):
    fn = engine.code[engine.pc]
    nargs = fn.nargs()
    d: Deque = deque()
    for _ in range(nargs):
        d.appendleft(engine.value_stack.pop())
    engine.value_stack.push(fn(*d))
    engine.pc += 1

def inst_sys_callq_2to1(engine: Engine):
    fn = engine.code[engine.pc]
    y = engine.value_stack.pop()
    x = engine.value_stack.pop()
    engine.value_stack.append(fn(x, y))
    engine.pc += 1

def inst_sys_callq_0to1(engine: Engine):
    fn = engine.code[engine.pc]
    engine.value_stack.push(fn())
    engine.pc += 1

def inst_pushq(engine: Engine):
    engine.value_stack.append(engine.code[engine.pc])
    engine.pc += 1

def inst_pop_local(engine: Engine):
    name = engine.code[engine.pc]
    engine.locals[name] = engine.value_stack.pop()
    engine.pc += 1

def inst_push_local(engine: Engine):
    name = engine.code[engine.pc]
    engine.value_stack.append(engine.locals[name])
    engine.pc += 1

def inst_pop_global(engine: Engine):
    name = engine.code[engine.pc]
    engine.globals[name] = engine.value_stack.pop()
    engine.pc += 1

def inst_push_global(engine: Engine):
    name = engine.code[engine.pc]
    engine.value_stack.append(engine.globals[name])
    engine.pc += 1

def inst_jump(engine: Engine):
    engine.pc = engine.code[engine.pc]

def inst_jump_if_not(engine: Engine):
    if not engine.value_stack.pop():
        engine.pc = engine.code[engine.pc]
    else:
        engine.pc += 1

class Procedure(ABC):
    @abstractmethod
    def callq(self, engine: Engine):
        ...

    @abstractmethod
    def show(self):
        ...

    @abstractmethod
    def __call__(self, *args):
        ...

class SysFn(Procedure):

    def __init__(self, fn):
        self._fn = fn

    def nargs(self):
        return len(signature(self._fn).parameters)

    def show(self):
        print(f'SysNto1: {self._fn}')

    def __call__(self, *args):
        return self._fn(*args)

class SysNto1(SysFn):

    def __init__(self, fn):
        super().__init__(fn)
        self._nargs = len(signature(fn).parameters)

    def nargs(self):
        return self._nargs

    def callq(self, engine: Engine):
        engine.sys_callq_Nto1(self._nargs, self._fn)

class Sys2to1(SysNto1):

    def nargs(self):
        return 2

    def callq(self, engine: Engine):
        engine.sys_callq_2to1(self._fn)

class Function(Procedure):

    def __init__(self):
        self._code = ()

    def init_code(self, code):
        '''We need a 2-stage initialisation because of the self-reference in the code.'''
        self._code = code

    def code(self):
        return self._code

    def callq(self, engine: Engine):
        engine.callq(self)

    def __call__(self, *args):
        engine = Engine()
        for arg in args:
            engine.pushq(arg)
        engine.callq(self)
        engine.run()
        return engine.returnValues()

    def show(self):
        for n, i in enumerate(self._code):
            print(f'{n}: {i}')

class Label:

    def __init__(self):
        self._offset = None
        self._dependents = []

    def add_dependent(self, d):
        self._dependents.append(d)

    def try_get_label(self):
        return self._offset

    def is_set_label(self):
        return self._offset is not None

    def set_label(self, offset):
        if self._offset is not None:
            raise RuntimeError('Label already set')
        if isinstance(offset, int):
            self._offset = offset
            for d in self._dependents:
                d(offset)
            self._dependents = None
        else:
            raise RuntimeError('Label must be a non-negative integer')

class CodePlanter:

    def __init__(self):
        self._code = []
        self._local_vars = set()
        self._nesting = []

    @abstractmethod
    def build(self):
        ...

    def _send_nesting(self, state):
        print(f'_send_nesting: {state} {self._nesting}')
        try:
            self._nesting[-1].send(state)
        except IndexError as exc:
            raise RuntimeError(f'Unexpected call of {state}') from exc
        except StopIteration:
            self._nesting.pop()
        return self

    def VAR(self, name: str):
        self._local_vars.add(name)
        return self

    def VARS(self, *names: str):
        for name in names:
            self._local_vars.add(name)
        return self

    def POP(self, name: str):
        if name in self._local_vars:
            self._code.append(inst_pop_local)
        else:
            self._code.append(inst_pop_global)
        self._code.append(name)
        return self

    def PUSH(self, name: str):
        if name in self._local_vars:
            self._code.append(inst_push_local)
        else:
            self._code.append(inst_push_global)
        self._code.append(name)
        return self

    def PUSHQ(self, value):
        self._code.append(inst_pushq)
        self._code.append(value)
        return self

    def CALLQ(self, fn: Procedure):
        if isinstance(fn, Function):
            self._code.append(inst_callq)
            self._code.append(fn)
        elif isinstance(fn, SysNto1):
            if fn.nargs() == 0:
                self._code.append(inst_sys_callq_0to1)
            elif fn.nargs() == 2:
                self._code.append(inst_sys_callq_2to1)
            else:
                self._code.append(inst_sys_callq_Nto1)
            self._code.append(fn)
        else:
            raise RuntimeError(f'Unknown procedure type: {fn}')
        return self

    def _set(self, n, offset):
        print(f'_set: {n} {offset}')
        self._code[n] = offset

    def _plant_label(self, label: Label):
        if label.is_set_label():
            self._code.append(label.try_get_label())
        else:
            n = len(self._code)
            self._code.append(None)
            label.add_dependent(lambda l: self._set(n, l))

    def NEW_LABEL(self):
        return Label()

    def LABEL(self, label: Label):
        label.set_label(len(self._code))

    def _IF(self):
        state = yield
        if state != 'THEN':
            raise RuntimeError(f'Expecting THEN but got: {state}')
        endif_label = self.NEW_LABEL()
        next_case_label = self.NEW_LABEL()
        self._code.append(inst_jump_if_not)
        self._plant_label(next_case_label)

        while True:
            state = yield
            print(f'_IF: {state}')
            if state == 'ENDIF':
                break
            if state == 'ELSE':
                self._code.append(inst_jump)
                self._plant_label(endif_label)
                self.LABEL(next_case_label)
                state = yield
                break
            if state == 'ELSEIF':
                self._code.append(inst_jump)
                self._plant_label(endif_label)
                self.LABEL(next_case_label)
                state = yield
                if state != 'THEN':
                    raise RuntimeError(f'Expecting THEN but got: {state}')
                next_case_label = self.NEW_LABEL()
                self._code.append(inst_jump_if_not)
                self._plant_label(next_case_label)
            else:
                raise RuntimeError(f'Expecting ELSE or ELSEIF but got: {state}')

        print(f'_IF should be endif: {state}')
        if state != 'ENDIF':
            raise RuntimeError(f'Expecting ENDIF but got: {state}')
        if not next_case_label.is_set_label():
            self.LABEL(next_case_label)
        self.LABEL(endif_label)

    def IF(self):
        g = self._IF()
        next(g)
        self._nesting.append(g)
        return self

    def THEN(self):
        return self._send_nesting('THEN')

    def ELSEIF(self):
        return self._send_nesting('ELSEIF')

    def ELSE(self):
        return self._send_nesting('ELSE')

    def ENDIF(self):
        return self._send_nesting('ENDIF')

    def _WHILE(self):
        startwhile_label = self.NEW_LABEL()
        self.LABEL(startwhile_label)

        state = yield
        if state != 'DO':
            raise RuntimeError(f'Expecting DO but got: {state}')

        endwhile_label = self.NEW_LABEL()

        self._code.append(inst_jump_if_not)
        self._plant_label(endwhile_label)

        state = yield
        if state != 'ENDWHILE':
            raise RuntimeError(f'Expecting ENDWHILE but got: {state}')

        self._code.append(inst_jump)
        self._plant_label(startwhile_label)

        self.LABEL(endwhile_label)

    def WHILE(self):
        g = self._WHILE()
        next(g)
        self._nesting.append(g)
        return self

    def DO(self):
        return self._send_nesting('DO')

    def ENDWHILE(self):
        return self._send_nesting('ENDWHILE')

class FunctionBuilder(CodePlanter):

    def __init__(self):
        super().__init__()
        self._code.append(None) # Placeholder

    def build(self):
        f = Function()
        self._code[0] = inst_enter  # Tie self-referencial knot.
        self._code.append(inst_leave)
        f.init_code(tuple(self._code))
        return f

ENVIRONMENT['>'] = Sys2to1(lambda x, y: x > y)
ENVIRONMENT['<'] = Sys2to1(lambda x, y: x < y)
