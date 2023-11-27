from vmcode import FunctionBuilder

def test_simple_vmcode():
    b = FunctionBuilder()
    b.VAR("x").POP("x").PUSH("x").PUSH("x")
    f = b.build()
    assert (1,2,3,3) == f(1, 2, 3)

def test_if1arm_vmcode():
    b = FunctionBuilder()
    b.IF().THEN().PUSHQ("a").ENDIF()
    f = b.build()
    f.show()
    assert ("a",) == f(True)
    assert () == f(False)

def test_if2arms_vmcode():
    b = FunctionBuilder()
    b.IF().THEN().PUSHQ("a").ELSE().PUSHQ("b").ENDIF()
    f = b.build()
    f.show()
    assert ("a",) == f(True)
    assert ("b",) == f(False)


def test_elseif_vmcode():
    b = FunctionBuilder()
    b.VARS('x', 'y').POP('y').POP('x')
    b.IF().PUSH('x').THEN().PUSHQ("a").ELSEIF().PUSH('y').THEN().PUSHQ('b').ELSE().PUSHQ("c").ENDIF()
    f = b.build()
    f.show()
    assert ("a",) == f(True, False)
    assert ("b",) == f(False, True)
    assert ("c",) == f(False, False)
