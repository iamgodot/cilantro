from cilantro import Cilantro


def test_cilantro():
    cilantro = Cilantro("Cilantro")
    assert cilantro() == "Hello world!"
