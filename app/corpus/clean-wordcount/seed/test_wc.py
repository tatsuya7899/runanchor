from wc import top_word

def test_top():
    assert top_word("a b a c b a") == "a"
